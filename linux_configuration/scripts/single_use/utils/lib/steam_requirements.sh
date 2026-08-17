#!/usr/bin/env bash
# Hardware detection and the parsing and scoring of Steam requirement text.
#
# detect_system writes the SYSTEM_* globals that score_game reads, so writer
# and readers sit in the same file - a file that assigns a global it never
# reads trips SC2034, which the repo forbids suppressing.

# Safe HTTP GET with optional timeout if available
http_get() {
  local url="$1"
  shift || true
  local ua="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
  if [[ $HAS_TIMEOUT -eq 1 ]]; then
    timeout 12s curl -sSL --compressed --retry 2 --retry-delay 0.5 --retry-connrefused \
      -H "User-Agent: $ua" -H 'Accept: application/json, text/plain, */*' "$url" "$@" 2> /dev/null
  else
    curl -sSL --compressed --retry 2 --retry-delay 0.5 --retry-connrefused \
      -H "User-Agent: $ua" -H 'Accept: application/json, text/plain, */*' "$url" "$@" 2> /dev/null
  fi
}

to_int() { awk '{gsub(/[^0-9]/,""); if($0=="") print 0; else print $0}' <<< "$1"; }

detect_system() {
  # CPU model
  if command -v lscpu > /dev/null 2>&1; then
    SYSTEM_CPU_MODEL=$(lscpu | awk -F': *' '/Model name/ {print $2; exit}')
  fi
  if [[ -z $SYSTEM_CPU_MODEL && -r /proc/cpuinfo ]]; then
    SYSTEM_CPU_MODEL=$(awk -F': *' '/model name/ {print $2; exit}' /proc/cpuinfo)
  fi
  SYSTEM_CPU_MODEL=${SYSTEM_CPU_MODEL:-unknown}

  # CPU class (very rough)
  lc_model=$(tr '[:upper:]' '[:lower:]' <<< "$SYSTEM_CPU_MODEL")
  if grep -qiE 'i9-|core\(tm\) i9| ryzen 9' <<< "$lc_model"; then
    SYSTEM_CPU_CLASS="tier4"
  elif grep -qiE 'i7-|core\(tm\) i7| ryzen 7' <<< "$lc_model"; then
    SYSTEM_CPU_CLASS="tier3"
  elif grep -qiE 'i5-|core\(tm\) i5| ryzen 5' <<< "$lc_model"; then
    SYSTEM_CPU_CLASS="tier2"
  elif grep -qiE 'i3-|core\(tm\) i3| ryzen 3| pentium|celeron|atom' <<< "$lc_model"; then
    SYSTEM_CPU_CLASS="tier1"
  else SYSTEM_CPU_CLASS="tier2"; fi

  # GPU vendor
  local vga
  vga=$(lspci 2> /dev/null | grep -iE 'vga|3d|display' | head -n1 || true)
  lc_vga=$(tr '[:upper:]' '[:lower:]' <<< "$vga")
  if grep -q 'nvidia' <<< "$lc_vga"; then
    SYSTEM_GPU_VENDOR="nvidia"
  elif grep -q -E 'amd|ati|radeon' <<< "$lc_vga"; then
    SYSTEM_GPU_VENDOR="amd"
  elif grep -q 'intel' <<< "$lc_vga"; then
    SYSTEM_GPU_VENDOR="intel"
  else SYSTEM_GPU_VENDOR="unknown"; fi

  # RAM GB
  local mem_kb
  mem_kb=$(awk '/MemTotal/ {print $2; exit}' /proc/meminfo 2> /dev/null || echo 0)
  if [[ $mem_kb -gt 0 ]]; then
    SYSTEM_RAM_GB=$(((mem_kb + 1023 * 1024) / (1024 * 1024)))
  else
    local mem_mb
    mem_mb=$(free -m | awk '/Mem:/ {print $2; exit}')
    SYSTEM_RAM_GB=$(((mem_mb + 1023) / 1024))
  fi
}

cpu_class_rank() {
  case "$1" in
    tier1) echo 1 ;;
    tier2) echo 2 ;;
    tier3) echo 3 ;;
    tier4) echo 4 ;;
    *) echo 2 ;;
  esac
}

required_cpu_rank_from_text() {
  local t
  t=$(tr '[:upper:]' '[:lower:]' <<< "$1")
  if grep -qE 'i9|ryzen 9' <<< "$t"; then
    echo 4
    return
  fi
  if grep -qE 'i7|ryzen 7' <<< "$t"; then
    echo 3
    return
  fi
  if grep -qE 'i5|ryzen 5' <<< "$t"; then
    echo 2
    return
  fi
  if grep -qE 'i3|ryzen 3|pentium|celeron|atom' <<< "$t"; then
    echo 1
    return
  fi
  echo 2
}

gpu_vendor_required_from_text() {
  local t
  t=$(tr '[:upper:]' '[:lower:]' <<< "$1")
  if grep -qE 'nvidia|geforce|gtx|rtx' <<< "$t"; then
    echo nvidia
    return
  fi
  if grep -qE 'amd|radeon|rx[ -]?[0-9]' <<< "$t"; then
    echo amd
    return
  fi
  if grep -qE 'intel( graphics| arc| iris| hd)' <<< "$t"; then
    echo intel
    return
  fi
  echo unknown
}

strip_html() {
  sed -E 's/<[^>]+>//g; s/&nbsp;/ /g; s/&amp;/\&/g; s/\r//g' <<< "$1"
}

parse_ram_gb() {
  # Extract first RAM mention and convert to GB integer
  local text="$1"
  local num val
  # Prefer GB
  num=$(grep -oiE '([0-9]+)\s*(gb|gib)' <<< "$text" | head -n1 | grep -oiE '^[0-9]+' || true)
  if [[ -n $num ]]; then
    echo "$num"
    return
  fi
  # Try MB
  num=$(grep -oiE '([0-9]+)\s*(mb|mib)' <<< "$text" | head -n1 | grep -oiE '^[0-9]+' || true)
  if [[ -n $num ]]; then
    val=$(((num + 1023) / 1024))
    echo "$val"
    return
  fi
  echo 0
}

score_game() {
  local linux_support="$1" min_txt="$2" rec_txt="$3"
  local score=0

  # Linux platform support
  if [[ $linux_support == "true" ]]; then
    score=$((score + 50))
  else
    score=$((score + 20)) # Assume Proton potential
  fi

  local min_plain rec_plain
  min_plain=$(strip_html "$min_txt")
  rec_plain=$(strip_html "$rec_txt")

  local min_ram rec_ram
  min_ram=$(parse_ram_gb "$min_plain")
  rec_ram=$(parse_ram_gb "$rec_plain")

  # RAM checks
  if [[ $min_ram -gt 0 ]]; then
    if [[ $SYSTEM_RAM_GB -ge $min_ram ]]; then score=$((score + 15)); else score=$((score - 30)); fi
  fi
  if [[ $rec_ram -gt 0 ]]; then
    if [[ $SYSTEM_RAM_GB -ge $rec_ram ]]; then score=$((score + 10)); else score=$((score - 10)); fi
  fi

  # CPU checks (very rough tiers)
  local req_rank sys_rank
  req_rank=$(required_cpu_rank_from_text "$min_plain $rec_plain")
  sys_rank=$(cpu_class_rank "$SYSTEM_CPU_CLASS")
  if [[ $sys_rank -ge $req_rank ]]; then score=$((score + 10)); else score=$((score - 10)); fi

  # GPU vendor hints
  local req_gpu vendor
  req_gpu=$(gpu_vendor_required_from_text "$min_plain $rec_plain")
  vendor="$SYSTEM_GPU_VENDOR"
  if [[ $req_gpu == "unknown" ]]; then
    score=$((score + 5))
  elif [[ $req_gpu == "$vendor" ]]; then
    score=$((score + 10))
  else
    score=$((score - 10))
  fi

  # 64-bit OS requirement
  if grep -qi '64-?bit' <<< "$min_plain $rec_plain"; then
    if [[ $SYSTEM_ARCH == "x86_64" || $SYSTEM_ARCH == "aarch64" ]]; then
      score=$((score + 5))
    else
      score=$((score - 20))
    fi
  fi

  printf "%s\t%s\t%s\n" "$score" "$min_ram" "$rec_ram"
}

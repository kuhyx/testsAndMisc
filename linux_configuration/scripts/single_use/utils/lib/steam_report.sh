#!/usr/bin/env bash
# The run loop and the on-disk cache for steam_compatibility.sh.
#
# load_cache_map writes CACHE_MAP and main reads it, so writer and reader sit
# in the same file.

load_cache_map() {
  CACHE_MAP=()
  if [[ -r $RESULTS_CACHE ]]; then
    while IFS= read -r raw_line; do
      # Normalize historical caches that contain literal "\t" instead of real tabs
      local norm_line
      norm_line=$(printf "%s" "$raw_line" | sed -E $'s/\\t/\t/g; s/\r$//')
      IFS=$'\t' read -r c_score c_appid c_linux c_min c_rec c_name c_pdb <<< "$norm_line"
      [[ -z ${c_appid:-} ]] && continue
      c_pdb=${c_pdb:-unknown}
      CACHE_MAP["$c_appid"]="$c_score\t$c_appid\t$c_linux\t$c_min\t$c_rec\t$c_name\t$c_pdb"
    done < "$RESULTS_CACHE"
  fi
}

main() {
  parse_args "$@"
  detect_system
  log "System: CPU=[$SYSTEM_CPU_MODEL] class=$SYSTEM_CPU_CLASS | GPU=$SYSTEM_GPU_VENDOR | RAM=${SYSTEM_RAM_GB}GB | Arch=$SYSTEM_ARCH"

  local tmpdir
  tmpdir=$(mktemp -d)
  trap '[[ -n "${tmpdir:-}" ]] && rm -rf "$tmpdir"' EXIT

  local games_tsv="$tmpdir/games.tsv"
  : > "$games_tsv"

  # Ensure credentials exist: load from env/config or prompt, else exit
  if ! load_credentials; then
    prompt_for_credentials
  fi

  # Fail fast if we cannot reach the store API to avoid noisy per-app errors
  check_network_or_exit

  if list_owned_games_via_api > "$games_tsv" 2> /dev/null; then
    log "Fetched owned games via Steam Web API"
  fi

  if [[ ! -s $games_tsv ]]; then
    die "No games found from Steam Web API. Check STEAM_API_KEY/STEAM_ID64 and network connectivity."
  fi

  # Fail fast if we cannot reach the store API to avoid noisy per-app errors
  check_network_or_exit

  ensure_cache_dir
  if [[ $CLEAR_CACHE -eq 1 ]] && [[ -f $RESULTS_CACHE ]]; then
    rm -f "$RESULTS_CACHE" || true
    log "Cleared cache: $RESULTS_CACHE"
  fi
  if [[ $FORCE_REFRESH -eq 0 ]]; then
    load_cache_map
  else
    CACHE_MAP=()
  fi

  local results_combined="$tmpdir/results.tsv"
  : > "$results_combined"

  local count=0
  local total
  total=$(wc -l < "$games_tsv" | tr -d ' ')
  [[ -z $total ]] && total=0
  while IFS=$'\t' read -r appid name; do
    [[ $ABORT -eq 1 ]] && break
    [[ -n $appid ]] || continue
    if is_known_tool_name "$name"; then
      vlog "[$((count + 1))/$total] Skipping compatibility tool: $name ($appid)"
      continue
    fi
    # If cached, reuse; else analyze and cache
    if [[ $FORCE_REFRESH -eq 0 && -n ${CACHE_MAP[$appid]+isset} ]]; then
      # Normalize to include ProtonDB column if older cache lacked it
      IFS=$'\t' read -r c_score c_a c_linux c_min c_rec c_name c_pdb <<< "${CACHE_MAP[$appid]}"
      c_pdb=${c_pdb:-unknown}
      vlog "[$((count + 1))/$total] Cache hit: $name ($appid) | ProtonDB=$c_pdb"
      printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$c_score" "$c_a" "$c_linux" "$c_min" "$c_rec" "$c_name" "$c_pdb" >> "$results_combined"
      continue
    fi
    count=$((count + 1))
    log "Analyzing: $name ($appid) [$count/$total]"
    local row url
    url="https://store.steampowered.com/api/appdetails?appids=${appid}&l=en&cc=us"
    vlog "[$count/$total] Fetching store appdetails: $url"
    # Be gentle with the store API
    sleep 0.1
    row=$(http_get "$url" | extract_requirements_and_platforms_stdin "$appid" || true)
    if [[ -z $row ]]; then continue; fi
    local status linux _windows _mac min_txt rec_txt type
    IFS=$'\t' read -r status linux _windows _mac min_txt rec_txt type <<< "$row"
    vlog "[$count/$total] Parsed store data: status=$status linux=$linux type=$type"
    # Occasionally Steam returns success=false spuriously; retry once
    if [[ $status != "ok" ]]; then
      vlog "[$count/$total] Store status=fail; retrying once..."
      sleep 0.3
      row=$(http_get "$url" | extract_requirements_and_platforms_stdin "$appid" || true)
      IFS=$'\t' read -r status linux _windows _mac min_txt rec_txt type <<< "$row"
      vlog "[$count/$total] After retry: status=$status"
    fi
    # Try filtered endpoint that often bypasses age/region gates
    if [[ $status != "ok" ]]; then
      local url2="https://store.steampowered.com/api/appdetails?appids=${appid}&filters=platforms,linux_requirements,pc_requirements,type&l=en&cc=us"
      vlog "[$count/$total] Retrying with filters: $url2"
      sleep 0.1
      row=$(http_get "$url2" | extract_requirements_and_platforms_stdin "$appid" || true)
      IFS=$'\t' read -r status linux _windows _mac min_txt rec_txt type <<< "$row"
      vlog "[$count/$total] Filtered fetch status=$status"
    fi
    if [[ $status != "ok" ]]; then continue; fi
    if [[ $type != "game" && $type != "dlc" && $type != "" ]]; then continue; fi
    # ProtonDB tier
    [[ $ABORT -eq 1 ]] && break
    local pdb_tier
    vlog "[$count/$total] Fetching ProtonDB tier for appid=$appid"
    pdb_tier=$(fetch_protondb_tier "$appid")
    vlog "[$count/$total] ProtonDB tier=$pdb_tier"

    # Compute hardware-based score
    local score_line s_score s_min_ram s_rec_ram
    score_line=$(score_game "$linux" "$min_txt" "$rec_txt")
    IFS=$'\t' read -r s_score s_min_ram s_rec_ram <<< "$score_line"

    # Gate by ProtonDB: if bronze or below -> mark unplayable and force low score
    if ! protondb_allowed "$pdb_tier"; then
      s_score=-999
    fi

    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$s_score" "$appid" "$linux" "$s_min_ram" "$s_rec_ram" "$name" "$pdb_tier" >> "$results_combined"
    vlog "[$count/$total] Scored and recorded: score=$s_score min=${s_min_ram}G rec=${s_rec_ram}G"
  done < "$games_tsv"

  if [[ ! -s $results_combined ]]; then
    die "No compatible entries parsed from store API."
  fi

  print_header
  local rank=0
  sort -t $'\t' -k1,1nr -k6,6 "$results_combined" | while IFS=$'\t' read -r score appid linux min_ram rec_ram name pdb_tier; do
    rank=$((rank + 1))
    local display_name="$name"
    if ! protondb_allowed "$pdb_tier"; then
      display_name="$name [UNPLAYABLE]"
    fi
    printf "%-5s  %-8s  %-6s  %-6s  %-8s  %-9s  %s\n" "$rank" "$score" "${min_ram}G" "${rec_ram}G" "$linux" "${pdb_tier:-unknown}" "$display_name"
  done

  # Persist updated results for future runs (only current library entries)
  cp -f "$results_combined" "$RESULTS_CACHE" 2> /dev/null || cat "$results_combined" > "$RESULTS_CACHE"
}

#!/usr/bin/env bash

# Steam game compatibility checker for Linux
#
# Features:
# - Gets your games either via Steam Web API (owned library) or by scanning installed appmanifests.
# - Fetches system requirements from Steam Store API (no key required).
# - Compares against your system (CPU, RAM, GPU vendor, OS/arch) with simple heuristics.
# - Ranks games from most to least likely to run.
#
# Optional env vars (for full library):
#   STEAM_API_KEY  - Your Steam Web API key
#   STEAM_ID64     - Your 64-bit Steam ID
#
# Dependencies: curl, jq, awk, sed, grep, sort, lspci, free, uname
# Recommended:   timeout (coreutils) to guard slow network calls

set -euo pipefail

SCRIPT_NAME=${0##*/}
ABORT=0
on_abort() {
	ABORT=1
	log "Aborted by user"
	exit 130
}
trap on_abort INT TERM

# --------------------------- CLI args ---------------------------

usage() {
	cat <<USAGE
Usage: $SCRIPT_NAME [--refresh] [--clear-cache] [--verbose] [--help]

Options:
  --refresh       Re-analyze all games and overwrite cache (ignore previous results).
	--clear-cache   Delete cached results before running (implies --refresh).
	-v, --verbose   Print detailed progress and HTTP/parse steps.
  -h, --help      Show this help message and exit.
USAGE
}

FORCE_REFRESH=0
CLEAR_CACHE=0
VERBOSE=0

parse_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
			--refresh)
				FORCE_REFRESH=1; shift ;;
			--clear-cache)
				CLEAR_CACHE=1; FORCE_REFRESH=1; shift ;;
			-v|--verbose)
				VERBOSE=1; shift ;;
			-h|--help)
				usage; exit 0 ;;
			*)
				die "Unknown option: $1 (use --help)" ;;
		esac
	done
}


log() { printf "[%s] %s\n" "$SCRIPT_NAME" "$*" >&2; }
die() { printf "[%s] ERROR: %s\n" "$SCRIPT_NAME" "$*" >&2; exit 1; }
vlog() { if [[ $VERBOSE -eq 1 ]]; then printf "[%s][verbose] %s\n" "$SCRIPT_NAME" "$*" >&2; fi }

require_cmd() {
	command -v "$1" >/dev/null 2>&1 || die "Missing dependency: $1"
}

for cmd in curl jq awk sed grep sort lspci free uname; do
	require_cmd "$cmd"
done

HAS_TIMEOUT=0
if command -v timeout >/dev/null 2>&1; then
	HAS_TIMEOUT=1
fi

# Safe HTTP GET with optional timeout if available
http_get() {
	local url="$1"
	shift || true
	local ua="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
	if [[ $HAS_TIMEOUT -eq 1 ]]; then
		timeout 12s curl -sSL --compressed --retry 2 --retry-delay 0.5 --retry-connrefused \
			-H "User-Agent: $ua" -H 'Accept: application/json, text/plain, */*' "$url" "$@" 2>/dev/null
	else
		curl -sSL --compressed --retry 2 --retry-delay 0.5 --retry-connrefused \
			-H "User-Agent: $ua" -H 'Accept: application/json, text/plain, */*' "$url" "$@" 2>/dev/null
	fi
}

# --------------------------- System detection ---------------------------

SYSTEM_CPU_MODEL=""
SYSTEM_CPU_CLASS="unknown"
SYSTEM_GPU_VENDOR="unknown"
SYSTEM_RAM_GB=0
SYSTEM_ARCH="$(uname -m || echo unknown)"
SYSTEM_OS="linux"

to_int() { awk '{gsub(/[^0-9]/,""); if($0=="") print 0; else print $0}' <<<"$1"; }

detect_system() {
	# CPU model
	if command -v lscpu >/dev/null 2>&1; then
		SYSTEM_CPU_MODEL=$(lscpu | awk -F': *' '/Model name/ {print $2; exit}')
	fi
	if [[ -z "$SYSTEM_CPU_MODEL" && -r /proc/cpuinfo ]]; then
		SYSTEM_CPU_MODEL=$(awk -F': *' '/model name/ {print $2; exit}' /proc/cpuinfo)
	fi
	SYSTEM_CPU_MODEL=${SYSTEM_CPU_MODEL:-unknown}

	# CPU class (very rough)
	lc_model=$(tr '[:upper:]' '[:lower:]' <<<"$SYSTEM_CPU_MODEL")
	if grep -qiE 'i9-|core\(tm\) i9| ryzen 9' <<<"$lc_model"; then SYSTEM_CPU_CLASS="tier4"; 
	elif grep -qiE 'i7-|core\(tm\) i7| ryzen 7' <<<"$lc_model"; then SYSTEM_CPU_CLASS="tier3"; 
	elif grep -qiE 'i5-|core\(tm\) i5| ryzen 5' <<<"$lc_model"; then SYSTEM_CPU_CLASS="tier2"; 
	elif grep -qiE 'i3-|core\(tm\) i3| ryzen 3| pentium|celeron|atom' <<<"$lc_model"; then SYSTEM_CPU_CLASS="tier1"; 
	else SYSTEM_CPU_CLASS="tier2"; fi

	# GPU vendor
	local vga
	vga=$(lspci 2>/dev/null | grep -iE 'vga|3d|display' | head -n1 || true)
	lc_vga=$(tr '[:upper:]' '[:lower:]' <<<"$vga")
	if grep -q 'nvidia' <<<"$lc_vga"; then SYSTEM_GPU_VENDOR="nvidia";
	elif grep -q -E 'amd|ati|radeon' <<<"$lc_vga"; then SYSTEM_GPU_VENDOR="amd";
	elif grep -q 'intel' <<<"$lc_vga"; then SYSTEM_GPU_VENDOR="intel";
	else SYSTEM_GPU_VENDOR="unknown"; fi

	# RAM GB
	local mem_kb
	mem_kb=$(awk '/MemTotal/ {print $2; exit}' /proc/meminfo 2>/dev/null || echo 0)
	if [[ "$mem_kb" -gt 0 ]]; then
		SYSTEM_RAM_GB=$(( (mem_kb + 1023*1024) / (1024*1024) ))
	else
		local mem_mb
		mem_mb=$(free -m | awk '/Mem:/ {print $2; exit}')
		SYSTEM_RAM_GB=$(( (mem_mb + 1023) / 1024 ))
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
	local t=$(tr '[:upper:]' '[:lower:]' <<<"$1")
	if grep -qE 'i9|ryzen 9' <<<"$t"; then echo 4; return; fi
	if grep -qE 'i7|ryzen 7' <<<"$t"; then echo 3; return; fi
	if grep -qE 'i5|ryzen 5' <<<"$t"; then echo 2; return; fi
	if grep -qE 'i3|ryzen 3|pentium|celeron|atom' <<<"$t"; then echo 1; return; fi
	echo 2
}

gpu_vendor_required_from_text() {
	local t=$(tr '[:upper:]' '[:lower:]' <<<"$1")
	if grep -qE 'nvidia|geforce|gtx|rtx' <<<"$t"; then echo nvidia; return; fi
	if grep -qE 'amd|radeon|rx[ -]?[0-9]' <<<"$t"; then echo amd; return; fi
	if grep -qE 'intel( graphics| arc| iris| hd)' <<<"$t"; then echo intel; return; fi
	echo unknown
}

strip_html() {
	sed -E 's/<[^>]+>//g; s/&nbsp;/ /g; s/&amp;/\&/g; s/\r//g' <<<"$1"
}

parse_ram_gb() {
	# Extract first RAM mention and convert to GB integer
	local text="$1"
	local num unit val
	# Prefer GB
	num=$(grep -oiE '([0-9]+)\s*(gb|gib)' <<<"$text" | head -n1 | grep -oiE '^[0-9]+' || true)
	if [[ -n "$num" ]]; then echo "$num"; return; fi
	# Try MB
	num=$(grep -oiE '([0-9]+)\s*(mb|mib)' <<<"$text" | head -n1 | grep -oiE '^[0-9]+' || true)
	if [[ -n "$num" ]]; then
		val=$(( (num + 1023) / 1024 ))
		echo "$val"; return
	fi
	echo 0
}

# --------------------------- Steam data ---------------------------

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/steam-compat-check"
CONFIG_FILE="$CONFIG_DIR/credentials.conf"

# Cache for analyzed results
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/steam-compat-check"
RESULTS_CACHE="$CACHE_DIR/results.tsv"

load_credentials() {
	# Prefer environment, else config file
	if [[ -n "${STEAM_API_KEY:-}" && -n "${STEAM_ID64:-}" ]]; then
		return 0
	fi
	if [[ -r "$CONFIG_FILE" ]]; then
		# shellcheck disable=SC1090
		. "$CONFIG_FILE" || true
	fi
	if [[ -z "${STEAM_API_KEY:-}" || -z "${STEAM_ID64:-}" ]]; then
		return 1
	fi
	return 0
}

save_credentials() {
	local key="$1" id="$2"
	mkdir -p "$CONFIG_DIR"
	chmod 700 "$CONFIG_DIR" 2>/dev/null || true
	umask 177
	cat > "$CONFIG_FILE" <<EOF
# Saved by $SCRIPT_NAME
STEAM_API_KEY="$key"
STEAM_ID64="$id"
EOF
}

prompt_for_credentials() {
	if [[ ! -t 0 ]]; then
		die "STEAM_API_KEY/STEAM_ID64 not set and input is non-interactive. Export them or create $CONFIG_FILE."
	fi
	echo "Steam Web API credentials are required to scan your full library."
	echo
	echo "Where to get them:"
	echo "- Steam Web API Key: https://steamcommunity.com/dev/apikey"
	echo "  Log in, set any domain (e.g., 127.0.0.1), then copy the key."
	echo "- SteamID64 (17-digit ID starting with 765):"
	echo "  * Easiest: https://steamid.io/ (paste your profile URL to get the 64-bit ID)"
	echo "  * Or enable URL bar in Steam (Settings > Interface), open your profile; the URL contains the ID."
	echo
	local key id
	read -r -p "Enter Steam Web API Key: " key
	read -r -p "Enter Steam 64-bit ID (begins with 765…): " id
	if [[ -z "$key" || -z "$id" ]]; then
		die "Credentials not provided. Exiting."
	fi
	# Light validation for ID64
	if ! grep -qE '^765[0-9]{14}$' <<<"$id"; then
		log "Warning: Steam ID64 format unexpected; continuing anyway."
	fi
	STEAM_API_KEY="$key"
	STEAM_ID64="$id"
	export STEAM_API_KEY STEAM_ID64
	save_credentials "$STEAM_API_KEY" "$STEAM_ID64"
	log "Saved credentials to $CONFIG_FILE"
}

STEAM_DIRS=( "$HOME/.steam/steam" "$HOME/.local/share/Steam" )

find_steamapps_dirs() {
	local dirs=()
	for base in "${STEAM_DIRS[@]}"; do
		[[ -d "$base" ]] || continue
		if [[ -f "$base/steamapps/libraryfolders.vdf" ]]; then
			# Newer format includes nested objects with paths
			local paths
			paths=$(grep -oE '"path"\s+"[^"]+"' "$base/steamapps/libraryfolders.vdf" | sed -E 's/.*"([^"]+)"/\1/' || true)
			if [[ -n "$paths" ]]; then
				while IFS= read -r p; do
					[[ -d "$p/steamapps" ]] && dirs+=("$p/steamapps")
				done <<<"$paths"
			fi
		fi
		[[ -d "$base/steamapps" ]] && dirs+=("$base/steamapps")
	done
	# de-dupe
	printf "%s\n" "${dirs[@]}" 2>/dev/null | awk '!seen[$0]++'
}

list_installed_games() {
	local d appid name
	while IFS= read -r d; do
		[[ -d "$d" ]] || continue
		for mf in "$d"/appmanifest_*.acf; do
			[[ -f "$mf" ]] || continue
			appid=$(grep -oE '"appid"\s+"[0-9]+"' "$mf" | sed -E 's/.*"([0-9]+)"/\1/' | head -n1)
			name=$(grep -oE '"name"\s+"[^"]+"' "$mf" | sed -E 's/.*"([^"]+)"/\1/' | head -n1)
			if [[ -n "$appid" ]]; then
				printf "%s\t%s\n" "$appid" "${name:-Unknown}"
			fi
		done
	done < <(find_steamapps_dirs)
}

list_owned_games_via_api() {
	local key="${STEAM_API_KEY:-}" sid="${STEAM_ID64:-}"
	if [[ -z "$key" || -z "$sid" ]]; then
	return 1
	fi
	local url="https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=${key}&steamid=${sid}&include_appinfo=1&include_played_free_games=1&format=json"
	http_get "$url" | jq -r '.response.games[]? | "\(.appid)\t\(.name)"' || return 1
}

fetch_appdetails_json() {
	local appid="$1"
	# Using store API (no key)
	local url="https://store.steampowered.com/api/appdetails?appids=${appid}&l=en&cc=us"
	http_get "$url" || true
}

extract_requirements_and_platforms() {
	# Input: JSON from appdetails; Output: TSV of fields
	# Fields: success, linux, windows, mac, min_text, rec_text, type
	local appid="$1" json="$2"
	# Some apps return {"APPID": {"success":true, "data":{...}}}
	local out
	out=$(jq -r --arg APP "$appid" '
		.[$APP] as $root | if ($root.success==true and ($root.data|type)=="object") then
			($root.data.platforms.linux // false) as $linux |
			($root.data.platforms.windows // false) as $windows |
			($root.data.platforms.mac // false) as $mac |
			($root.data.type // "") as $type |
			# Prefer Linux reqs when present
			($root.data.linux_requirements.minimum // $root.data.pc_requirements.minimum // "") as $min |
			($root.data.linux_requirements.recommended // $root.data.pc_requirements.recommended // "") as $rec |
			["ok", ($linux|tostring), ($windows|tostring), ($mac|tostring), ($min|tostring), ($rec|tostring), ($type|tostring)] | @tsv
		else
			["fail", "false", "false", "false", "", "", ""] | @tsv
		end' 2>/dev/null <<<"$json") || true
	if [[ -z "$out" ]]; then
		out=$'fail	false	false	false			'
	fi
	printf '%s\n' "$out"
}

# Read JSON from stdin (avoids storing large/binary data in variables)
extract_requirements_and_platforms_stdin() {
	local appid="$1"
	local out
	out=$(jq -r --arg APP "$appid" '
		.[$APP] as $root | if ($root.success==true and ($root.data|type)=="object") then
			($root.data.platforms.linux // false) as $linux |
			($root.data.platforms.windows // false) as $windows |
			($root.data.platforms.mac // false) as $mac |
			($root.data.type // "") as $type |
			($root.data.linux_requirements.minimum // $root.data.pc_requirements.minimum // "") as $min |
			($root.data.linux_requirements.recommended // $root.data.pc_requirements.recommended // "") as $rec |
			["ok", ($linux|tostring), ($windows|tostring), ($mac|tostring), ($min|tostring), ($rec|tostring), ($type|tostring)] | @tsv
		else
			["fail", "false", "false", "false", "", "", ""] | @tsv
		end' 2>/dev/null) || true
	if [[ -z "$out" ]]; then
		out=$'fail\tfalse\tfalse\tfalse\t\t\t'
	fi
	printf '%s\n' "$out"
}

score_game() {
	local linux_support="$1" min_txt="$2" rec_txt="$3"
	local score=0

	# Linux platform support
	if [[ "$linux_support" == "true" ]]; then
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
	if [[ "$min_ram" -gt 0 ]]; then
		if [[ "$SYSTEM_RAM_GB" -ge "$min_ram" ]]; then score=$((score + 15)); else score=$((score - 30)); fi
	fi
	if [[ "$rec_ram" -gt 0 ]]; then
		if [[ "$SYSTEM_RAM_GB" -ge "$rec_ram" ]]; then score=$((score + 10)); else score=$((score - 10)); fi
	fi

	# CPU checks (very rough tiers)
	local req_rank sys_rank
	req_rank=$(required_cpu_rank_from_text "$min_plain $rec_plain")
	sys_rank=$(cpu_class_rank "$SYSTEM_CPU_CLASS")
	if [[ "$sys_rank" -ge "$req_rank" ]]; then score=$((score + 10)); else score=$((score - 10)); fi

	# GPU vendor hints
	local req_gpu vendor
	req_gpu=$(gpu_vendor_required_from_text "$min_plain $rec_plain")
	vendor="$SYSTEM_GPU_VENDOR"
	if [[ "$req_gpu" == "unknown" ]]; then
		score=$((score + 5))
	elif [[ "$req_gpu" == "$vendor" ]]; then
		score=$((score + 10))
	else
		score=$((score - 10))
	fi

	# 64-bit OS requirement
	if grep -qi '64-?bit' <<<"$min_plain $rec_plain"; then
		if [[ "$SYSTEM_ARCH" == "x86_64" || "$SYSTEM_ARCH" == "aarch64" ]]; then
			score=$((score + 5))
		else
			score=$((score - 20))
		fi
	fi

	printf "%s\t%s\t%s\n" "$score" "$min_ram" "$rec_ram"
}

print_header() {
	printf "%-5s  %-8s  %-6s  %-6s  %-8s  %-9s  %s\n" "Rank" "Score" "MinRAM" "RecRAM" "Linux" "ProtonDB" "Title"
}

check_network_or_exit() {
	# Quick probe to Steam Store API; exit early if not reachable
	local probe_url="https://store.steampowered.com/api/appdetails?appids=10&l=en&cc=us"
	if ! http_get "$probe_url" | jq -e '."10".success == true' >/dev/null 2>&1; then
		log "Warning: store.steampowered.com probe failed (network or rate-limit). Continuing and handling per-app."
	fi
}

is_known_tool_name() {
	local name_lc
	name_lc=$(tr '[:upper:]' '[:lower:]' <<<"$1")
	if grep -qE 'steam linux runtime|proton|compatibility tool' <<<"$name_lc"; then
		return 0
	fi
	return 1
}

ensure_cache_dir() {
	mkdir -p "$CACHE_DIR" 2>/dev/null || true
}

declare -A CACHE_MAP
load_cache_map() {
	CACHE_MAP=()
	if [[ -r "$RESULTS_CACHE" ]]; then
		while IFS= read -r raw_line; do
			# Normalize historical caches that contain literal "\t" instead of real tabs
			local norm_line
			norm_line=$(printf "%s" "$raw_line" | sed -E $'s/\\t/\t/g; s/\r$//')
			IFS=$'\t' read -r c_score c_appid c_linux c_min c_rec c_name c_pdb <<<"$norm_line"
			[[ -z "${c_appid:-}" ]] && continue
			c_pdb=${c_pdb:-unknown}
			CACHE_MAP["$c_appid"]="$c_score\t$c_appid\t$c_linux\t$c_min\t$c_rec\t$c_name\t$c_pdb"
		done < "$RESULTS_CACHE"
	fi
}

# --------------------------- ProtonDB integration ---------------------------

fetch_protondb_tier() {
	local appid="$1"
	local url="https://www.protondb.com/api/v1/reports/summaries/${appid}.json"
	# Returns minimal JSON including .tier, .confidence; we only need .tier
	local tier
	tier=$(http_get "$url" | jq -r 'try .tier // "unknown"' 2>/dev/null || true)
	if [[ -z "$tier" || "$tier" == "null" ]]; then
		echo "unknown"
	else
		tr '[:upper:]' '[:lower:]' <<<"$tier" | tr -d '\r\n'
	fi
}

protondb_allowed() {
	local tier="$(tr '[:upper:]' '[:lower:]' <<<"${1:-}")"
	case "$tier" in
		platinum|native|gold|silver|unknown|"") return 0 ;;
		bronze|pending|borked|unsupported|broken) return 1 ;;
		*) return 0 ;;
	esac
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

	if list_owned_games_via_api > "$games_tsv" 2>/dev/null; then
		log "Fetched owned games via Steam Web API"
	fi

	if [[ ! -s "$games_tsv" ]]; then
		die "No games found from Steam Web API. Check STEAM_API_KEY/STEAM_ID64 and network connectivity."
	fi

	# Fail fast if we cannot reach the store API to avoid noisy per-app errors
	check_network_or_exit

	ensure_cache_dir
	if [[ $CLEAR_CACHE -eq 1 ]] && [[ -f "$RESULTS_CACHE" ]]; then
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
	[[ -z "$total" ]] && total=0
	while IFS=$'\t' read -r appid name; do
	[[ $ABORT -eq 1 ]] && break
		[[ -n "$appid" ]] || continue
		if is_known_tool_name "$name"; then
			vlog "[$((count+1))/$total] Skipping compatibility tool: $name ($appid)"
			continue
		fi
		# If cached, reuse; else analyze and cache
		if [[ $FORCE_REFRESH -eq 0 && -n "${CACHE_MAP[$appid]+isset}" ]]; then
			# Normalize to include ProtonDB column if older cache lacked it
			IFS=$'\t' read -r c_score c_a c_linux c_min c_rec c_name c_pdb <<<"${CACHE_MAP[$appid]}"
			c_pdb=${c_pdb:-unknown}
			vlog "[$((count+1))/$total] Cache hit: $name ($appid) | ProtonDB=$c_pdb"
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
		if [[ -z "$row" ]]; then continue; fi
		local status linux windows mac min_txt rec_txt type
		IFS=$'\t' read -r status linux windows mac min_txt rec_txt type <<<"$row"
		vlog "[$count/$total] Parsed store data: status=$status linux=$linux type=$type"
		# Occasionally Steam returns success=false spuriously; retry once
		if [[ "$status" != "ok" ]]; then
			vlog "[$count/$total] Store status=fail; retrying once..."
			sleep 0.3
			row=$(http_get "$url" | extract_requirements_and_platforms_stdin "$appid" || true)
			IFS=$'\t' read -r status linux windows mac min_txt rec_txt type <<<"$row"
			vlog "[$count/$total] After retry: status=$status"
		fi
		# Try filtered endpoint that often bypasses age/region gates
		if [[ "$status" != "ok" ]]; then
			local url2="https://store.steampowered.com/api/appdetails?appids=${appid}&filters=platforms,linux_requirements,pc_requirements,type&l=en&cc=us"
			vlog "[$count/$total] Retrying with filters: $url2"
			sleep 0.1
			row=$(http_get "$url2" | extract_requirements_and_platforms_stdin "$appid" || true)
			IFS=$'\t' read -r status linux windows mac min_txt rec_txt type <<<"$row"
			vlog "[$count/$total] Filtered fetch status=$status"
		fi
		if [[ "$status" != "ok" ]]; then continue; fi
		if [[ "$type" != "game" && "$type" != "dlc" && "$type" != "" ]]; then continue; fi
		# ProtonDB tier
	[[ $ABORT -eq 1 ]] && break
		local pdb_tier
		vlog "[$count/$total] Fetching ProtonDB tier for appid=$appid"
		pdb_tier=$(fetch_protondb_tier "$appid")
		vlog "[$count/$total] ProtonDB tier=$pdb_tier"

		# Compute hardware-based score
		local score_line s_score s_min_ram s_rec_ram
		score_line=$(score_game "$linux" "$min_txt" "$rec_txt")
		IFS=$'\t' read -r s_score s_min_ram s_rec_ram <<<"$score_line"

		# Gate by ProtonDB: if bronze or below -> mark unplayable and force low score
		if ! protondb_allowed "$pdb_tier"; then
			s_score=-999
		fi

		printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$s_score" "$appid" "$linux" "$s_min_ram" "$s_rec_ram" "$name" "$pdb_tier" >> "$results_combined"
	vlog "[$count/$total] Scored and recorded: score=$s_score min=${s_min_ram}G rec=${s_rec_ram}G"
	done < "$games_tsv"

	if [[ ! -s "$results_combined" ]]; then
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
	cp -f "$results_combined" "$RESULTS_CACHE" 2>/dev/null || cat "$results_combined" > "$RESULTS_CACHE"
}

main "$@"


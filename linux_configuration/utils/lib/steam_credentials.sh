#!/usr/bin/env bash
# Credential storage, usage text and small presentation helpers.
#
# load_cache_map stays in the entry script beside the code that reads
# CACHE_MAP, so no file assigns a global it never reads.

usage() {
  cat << USAGE
Usage: $SCRIPT_NAME [--refresh] [--clear-cache] [--verbose] [--help]

Options:
  --refresh       Re-analyze all games and overwrite cache (ignore previous results).
	--clear-cache   Delete cached results before running (implies --refresh).
	-v, --verbose   Print detailed progress and HTTP/parse steps.
  -h, --help      Show this help message and exit.
USAGE
}

require_cmd() {
  command -v "$1" > /dev/null 2>&1 || die "Missing dependency: $1"
}

load_credentials() {
  # Prefer environment, else config file
  if [[ -n ${STEAM_API_KEY:-} && -n ${STEAM_ID64:-} ]]; then
    return 0
  fi
  if [[ -r $CONFIG_FILE ]]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE" || true
  fi
  if [[ -z ${STEAM_API_KEY:-} || -z ${STEAM_ID64:-} ]]; then
    return 1
  fi
  return 0
}

save_credentials() {
  local key="$1" id="$2"
  mkdir -p "$CONFIG_DIR"
  chmod 700 "$CONFIG_DIR" 2> /dev/null || true
  umask 177
  cat > "$CONFIG_FILE" << EOF
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
  if [[ -z $key || -z $id ]]; then
    die "Credentials not provided. Exiting."
  fi
  # Light validation for ID64
  if ! grep -qE '^765[0-9]{14}$' <<< "$id"; then
    log "Warning: Steam ID64 format unexpected; continuing anyway."
  fi
  STEAM_API_KEY="$key"
  STEAM_ID64="$id"
  export STEAM_API_KEY STEAM_ID64
  save_credentials "$STEAM_API_KEY" "$STEAM_ID64"
  log "Saved credentials to $CONFIG_FILE"
}

print_header() {
  printf "%-5s  %-8s  %-6s  %-6s  %-8s  %-9s  %s\n" "Rank" "Score" "MinRAM" "RecRAM" "Linux" "ProtonDB" "Title"
}

check_network_or_exit() {
  # Quick probe to Steam Store API; exit early if not reachable
  local probe_url="https://store.steampowered.com/api/appdetails?appids=10&l=en&cc=us"
  if ! http_get "$probe_url" | jq -e '."10".success == true' > /dev/null 2>&1; then
    log "Warning: store.steampowered.com probe failed (network or rate-limit). Continuing and handling per-app."
  fi
}

is_known_tool_name() {
  local name_lc
  name_lc=$(tr '[:upper:]' '[:lower:]' <<< "$1")
  if grep -qE 'steam linux runtime|proton|compatibility tool' <<< "$name_lc"; then
    return 0
  fi
  return 1
}

ensure_cache_dir() {
  mkdir -p "$CACHE_DIR" 2> /dev/null || true
}

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

# shellcheck source=lib/steam_report.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/steam_report.sh"

# shellcheck source=lib/steam_credentials.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/steam_credentials.sh"

# shellcheck source=lib/steam_api.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/steam_api.sh"

# shellcheck source=lib/steam_requirements.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/steam_requirements.sh"

SCRIPT_NAME=${0##*/}
ABORT=0
on_abort() {
  ABORT=1
  log "Aborted by user"
  exit 130
}
trap on_abort INT TERM

# --------------------------- CLI args ---------------------------


FORCE_REFRESH=0
CLEAR_CACHE=0
VERBOSE=0

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --refresh)
        FORCE_REFRESH=1
        shift
        ;;
      --clear-cache)
        CLEAR_CACHE=1
        FORCE_REFRESH=1
        shift
        ;;
      -v | --verbose)
        VERBOSE=1
        shift
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1 (use --help)"
        ;;
    esac
  done
}

log() { printf "[%s] %s\n" "$SCRIPT_NAME" "$*" >&2; }
die() {
  printf "[%s] ERROR: %s\n" "$SCRIPT_NAME" "$*" >&2
  exit 1
}
vlog() { if [[ $VERBOSE -eq 1 ]]; then printf "[%s][verbose] %s\n" "$SCRIPT_NAME" "$*" >&2; fi; }


for cmd in curl jq awk sed grep sort lspci free uname; do
  require_cmd "$cmd"
done

HAS_TIMEOUT=0
if command -v timeout > /dev/null 2>&1; then
  HAS_TIMEOUT=1
fi


# --------------------------- System detection ---------------------------

SYSTEM_CPU_MODEL=""
SYSTEM_CPU_CLASS="unknown"
SYSTEM_GPU_VENDOR="unknown"
SYSTEM_RAM_GB=0
SYSTEM_ARCH="$(uname -m || echo unknown)"








# --------------------------- Steam data ---------------------------

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/steam-compat-check"
CONFIG_FILE="$CONFIG_DIR/credentials.conf"

# Cache for analyzed results
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/steam-compat-check"
RESULTS_CACHE="$CACHE_DIR/results.tsv"




STEAM_DIRS=("$HOME/.steam/steam" "$HOME/.local/share/Steam")












declare -A CACHE_MAP

# --------------------------- ProtonDB integration ---------------------------




main "$@"

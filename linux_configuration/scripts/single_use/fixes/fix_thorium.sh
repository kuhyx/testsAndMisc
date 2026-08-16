#!/usr/bin/env bash

# Fix Thorium Browser crashes and startup issues
#
# Common causes addressed:
# - Corrupted Local State file (most common)
# - Stale singleton lock files
# - Corrupted GPU/shader cache
# - Profile database corruption
#
# Usage:
#   ./fix_thorium.sh              # Auto-fix common issues
#   ./fix_thorium.sh --aggressive # Also clear more caches (may lose some settings)
#   ./fix_thorium.sh --test       # Test if Thorium starts after fix

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

# Configuration
THORIUM_CONFIG_DIR="${HOME}/.config/thorium"
BACKUP_SUFFIX=".bak.$(date +%Y%m%d_%H%M%S)"
AGGRESSIVE=false
TEST_AFTER=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
  cat << EOF
fix_thorium.sh - Fix Thorium Browser crashes and startup issues

Usage: $(basename "$0") [OPTIONS]

Options:
  --aggressive    Clear additional caches (IndexedDB, Service Worker, etc.)
                  May cause loss of some site data but more thorough fix
  --test          Test if Thorium starts successfully after applying fixes
  --dry-run       Show what would be done without making changes
  -h, --help      Show this help message

Common issues fixed:
  - Corrupted 'Local State' file (causes immediate segfault)
  - Stale singleton lock files (prevents startup)
  - Corrupted GPU/shader cache
  - Crashpad errors

Examples:
  $(basename "$0")              # Apply standard fixes
  $(basename "$0") --test       # Fix and verify browser starts
  $(basename "$0") --aggressive # Deep clean (use if standard fix fails)
EOF
}

DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --aggressive)
      AGGRESSIVE=true
      shift
      ;;
    --test)
      TEST_AFTER=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

# Check if Thorium is installed
check_thorium_installed() {
  if ! command -v thorium-browser &> /dev/null; then
    log_error "thorium-browser not found in PATH"
    echo -e "${YELLOW}Install with: yay -S thorium-browser-bin${NC}"
    exit 1
  fi
  log_info "Found Thorium: $(thorium-browser --version 2> /dev/null | head -1)"
}

# Check if config directory exists
check_config_exists() {
  if [[ ! -d $THORIUM_CONFIG_DIR ]]; then
    log_warn "Thorium config directory not found: $THORIUM_CONFIG_DIR"
    log_info "This may be a fresh install - try running thorium-browser directly"
    exit 0
  fi
}

# Kill any running Thorium processes
kill_thorium() {
  local count
  count=$(pgrep -c thorium 2> /dev/null || true)
  count=${count:-0}

  if [[ $count -gt 0 ]]; then
    log_info "Stopping $count running Thorium process(es)..."
    if [[ $DRY_RUN == true ]]; then
      echo "  [dry-run] Would kill thorium processes"
    else
      pkill -9 thorium 2> /dev/null || true
      sleep 1
    fi
  fi
}

# Backup a file/directory if it exists
backup_if_exists() {
  local path="$1"
  local name
  name=$(basename "$path")

  if [[ -e $path ]]; then
    local backup_path="${path}${BACKUP_SUFFIX}"
    if [[ $DRY_RUN == true ]]; then
      echo "  [dry-run] Would backup: $name"
    else
      mv "$path" "$backup_path"
      log_ok "Backed up: $name -> $(basename "$backup_path")"
    fi
    return 0
  fi
  return 1
}

# Remove file/directory if it exists
remove_if_exists() {
  local path="$1"
  local name
  name=$(basename "$path")

  if [[ -e $path ]]; then
    if [[ $DRY_RUN == true ]]; then
      echo "  [dry-run] Would remove: $name"
    else
      rm -rf "$path"
      log_ok "Removed: $name"
    fi
    return 0
  fi
  return 1
}

# shellcheck source=lib/thorium_repairs.sh
source "$SCRIPT_DIR/lib/thorium_repairs.sh"

main() {
  echo "========================================"
  echo "  Thorium Browser Fix Script"
  echo "========================================"
  echo ""

  if [[ $DRY_RUN == true ]]; then
    echo -e "${YELLOW}[DRY RUN MODE - no changes will be made]${NC}"
    echo ""
  fi

  check_thorium_installed
  check_config_exists

  echo ""
  log_info "Applying fixes to: $THORIUM_CONFIG_DIR"
  echo ""

  kill_thorium
  fix_local_state
  fix_singleton_locks
  fix_gpu_cache
  fix_crash_reports
  fix_aggressive

  echo ""
  echo "========================================"
  log_ok "Fixes applied!"
  echo "========================================"

  if [[ $DRY_RUN != true ]]; then
    echo ""
    echo "Backups created with suffix: $BACKUP_SUFFIX"
    echo "To restore: mv ~/.config/thorium/Local\\ State${BACKUP_SUFFIX} ~/.config/thorium/Local\\ State"
  fi

  test_thorium

  if [[ $TEST_AFTER != true ]]; then
    echo ""
    echo "Run 'thorium-browser' to test, or use: $(basename "$0") --test"
  fi
}

main "$@"

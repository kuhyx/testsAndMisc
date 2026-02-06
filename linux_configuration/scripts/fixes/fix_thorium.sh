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
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

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

# Fix 1: Handle corrupted Local State file (most common crash cause)
fix_local_state() {
  log_info "Checking Local State file..."
  local local_state="$THORIUM_CONFIG_DIR/Local State"

  if [[ -f $local_state ]]; then
    # Check if it's valid JSON
    if ! python3 -c "import json; json.load(open('$local_state'))" 2> /dev/null; then
      log_warn "Local State file appears corrupted"
      backup_if_exists "$local_state"
    else
      # Even if valid JSON, back it up as it can still cause crashes
      log_info "Local State exists - backing up (common crash source)"
      backup_if_exists "$local_state"
    fi
  else
    log_info "No Local State file found (OK for fresh install)"
  fi
}

# Fix 2: Clear singleton lock files
fix_singleton_locks() {
  log_info "Clearing singleton lock files..."
  local locks=(
    "$THORIUM_CONFIG_DIR/SingletonLock"
    "$THORIUM_CONFIG_DIR/SingletonSocket"
    "$THORIUM_CONFIG_DIR/SingletonCookie"
  )

  local cleared=0
  for lock in "${locks[@]}"; do
    if remove_if_exists "$lock"; then
      ((cleared++)) || true
    fi
  done

  if [[ $cleared -eq 0 ]]; then
    log_info "No stale lock files found"
  fi
}

# Fix 3: Clear GPU cache
fix_gpu_cache() {
  log_info "Clearing GPU cache..."
  local gpu_paths=(
    "$THORIUM_CONFIG_DIR/GPUCache"
    "$THORIUM_CONFIG_DIR/Default/GPUCache"
    "$THORIUM_CONFIG_DIR/ShaderCache"
    "$THORIUM_CONFIG_DIR/Default/ShaderCache"
  )

  local cleared=0
  for cache in "${gpu_paths[@]}"; do
    if remove_if_exists "$cache"; then
      ((cleared++)) || true
    fi
  done

  if [[ $cleared -eq 0 ]]; then
    log_info "No GPU cache to clear"
  fi
}

# Fix 4: Clear crash reports (can accumulate and cause issues)
fix_crash_reports() {
  log_info "Clearing old crash reports..."
  local crash_dir="$THORIUM_CONFIG_DIR/Crash Reports"

  if [[ -d $crash_dir ]]; then
    local crash_count
    crash_count=$(find "$crash_dir" -type f 2> /dev/null | wc -l)
    if [[ $crash_count -gt 0 ]]; then
      if [[ $DRY_RUN == true ]]; then
        echo "  [dry-run] Would clear $crash_count crash report(s)"
      else
        rm -rf "$crash_dir"
        log_ok "Cleared $crash_count crash report(s)"
      fi
    fi
  fi
}

# Fix 5: Aggressive cleaning (optional)
fix_aggressive() {
  if [[ $AGGRESSIVE != true ]]; then
    return
  fi

  log_warn "Applying aggressive fixes (may lose some site data)..."

  local aggressive_paths=(
    "$THORIUM_CONFIG_DIR/Default/Service Worker"
    "$THORIUM_CONFIG_DIR/Default/Cache"
    "$THORIUM_CONFIG_DIR/Default/Code Cache"
    "$THORIUM_CONFIG_DIR/Default/IndexedDB"
    "$THORIUM_CONFIG_DIR/BrowserMetrics"
    "$THORIUM_CONFIG_DIR/component_crx_cache"
  )

  for path in "${aggressive_paths[@]}"; do
    remove_if_exists "$path"
  done

  # Backup potentially corrupted databases
  local db_files=(
    "$THORIUM_CONFIG_DIR/Default/Web Data"
    "$THORIUM_CONFIG_DIR/Default/History"
  )

  for db in "${db_files[@]}"; do
    if [[ -f $db ]]; then
      log_info "Checking database: $(basename "$db")"
      # Simple corruption check - if sqlite3 can't open it, back it up
      if command -v sqlite3 &> /dev/null; then
        if ! sqlite3 "$db" "PRAGMA integrity_check;" &> /dev/null; then
          log_warn "Database may be corrupted: $(basename "$db")"
          backup_if_exists "$db"
        fi
      fi
    fi
  done
}

# Test if Thorium starts successfully
test_thorium() {
  if [[ $TEST_AFTER != true ]]; then
    return
  fi

  log_info "Testing Thorium startup..."

  if [[ $DRY_RUN == true ]]; then
    echo "  [dry-run] Would test thorium-browser startup"
    return
  fi

  # Start Thorium in background
  thorium-browser &> /dev/null &
  local pid=$!

  # Wait a few seconds and check if it's still running
  sleep 4

  if kill -0 "$pid" 2> /dev/null; then
    log_ok "Thorium started successfully! (PID: $pid)"
    echo -e "${GREEN}Fix successful!${NC} Thorium is now running."

    # Offer to keep it running or kill it
    read -r -p "Keep browser running? [Y/n] " response
    case "$response" in
      [nN]*)
        kill "$pid" 2> /dev/null || true
        log_info "Browser closed"
        ;;
      *)
        log_info "Browser left running"
        ;;
    esac
  else
    log_error "Thorium still crashing after fixes"
    echo -e "${RED}Standard fixes did not resolve the issue.${NC}"
    echo ""
    echo "Try these additional steps:"
    echo "  1. Run with --aggressive flag for deeper cleaning"
    echo "  2. Test with fresh profile: thorium-browser --user-data-dir=/tmp/thorium-test"
    echo "  3. Reinstall: yay -S thorium-browser-bin"
    echo "  4. Check NVIDIA drivers: nvidia-smi"
    exit 1
  fi
}

# Main execution
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

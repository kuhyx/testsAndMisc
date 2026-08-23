#!/usr/bin/env bash

# Fix Anki startup issues caused by Python version mismatch or aqt namespace conflict
#
# Common causes addressed:
# - anki-git built for older Python version (e.g., 3.13) while system runs newer (e.g., 3.14)
# - python-aqtinstall package conflicts with Anki's aqt module (same namespace)
#
# Usage:
#   ./fix_anki.sh              # Auto-fix (rebuild anki-git)
#   ./fix_anki.sh --check      # Only check for issues, don't fix

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CHECK_ONLY=false

usage() {
  cat << EOF
fix_anki.sh - Fix Anki startup issues

Usage: $(basename "$0") [OPTIONS]

Options:
  --check    Only check for issues, don't apply fixes
  -h, --help Show this help message

Common issues fixed:
  - Python version mismatch (anki built for older Python)
  - aqt namespace conflict with python-aqtinstall

EOF
}

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }

check_anki_installed() {
  if pacman -Qi anki-git &> /dev/null; then
    echo "anki-git"
  elif pacman -Qi anki &> /dev/null; then
    echo "anki"
  elif pacman -Qi anki-bin &> /dev/null; then
    echo "anki-bin"
  else
    echo ""
  fi
}

get_system_python_version() {
  python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
}

get_anki_python_version() {
  local anki_pkg="$1"
  local anki_path
  anki_path=$(pacman -Ql "$anki_pkg" 2> /dev/null | grep -oP '/usr/lib/python\K[0-9]+\.[0-9]+' | head -1)
  echo "$anki_path"
}

check_aqt_conflict() {
  local sys_python="$1"
  local aqt_path="/usr/lib/python${sys_python}/site-packages/aqt/__init__.py"

  if [[ -f $aqt_path ]]; then
    if grep -q "aqtinstall" "$aqt_path" 2> /dev/null; then
      echo "aqtinstall"
    elif grep -q "anki" "$aqt_path" 2> /dev/null; then
      echo "anki"
    else
      echo "unknown"
    fi
  else
    echo "none"
  fi
}

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check)
        CHECK_ONLY=true
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

  log_info "Checking Anki installation..."

  # Check which Anki package is installed
  local anki_pkg
  anki_pkg=$(check_anki_installed)
  if [[ -z $anki_pkg ]]; then
    log_error "Anki is not installed"
    exit 1
  fi
  log_info "Found Anki package: $anki_pkg"

  # Get Python versions
  local sys_python anki_python
  sys_python=$(get_system_python_version)
  anki_python=$(get_anki_python_version "$anki_pkg")

  log_info "System Python version: $sys_python"
  log_info "Anki built for Python: ${anki_python:-unknown}"

  local issues_found=false

  # Check for Python version mismatch
  if [[ -n $anki_python && $sys_python != "$anki_python" ]]; then
    log_warn "Python version mismatch detected!"
    log_warn "  Anki was built for Python $anki_python but system runs Python $sys_python"
    issues_found=true
  fi

  # Check for aqt namespace conflict
  local aqt_owner
  aqt_owner=$(check_aqt_conflict "$sys_python")
  case "$aqt_owner" in
    aqtinstall)
      log_warn "aqt namespace conflict detected!"
      log_warn "  python-aqtinstall owns /usr/lib/python${sys_python}/site-packages/aqt/"
      log_warn "  This conflicts with Anki's aqt module"
      issues_found=true
      ;;
    anki)
      log_success "aqt module belongs to Anki (correct)"
      ;;
    none)
      if [[ $sys_python != "$anki_python" ]]; then
        log_warn "No aqt module found for Python $sys_python"
      fi
      ;;
    *)
      log_warn "Unknown aqt module owner"
      ;;
  esac

  # Test if Anki actually works
  log_info "Testing Anki startup..."
  if python -c "from aqt import run" 2> /dev/null; then
    log_success "Anki imports work correctly"
    if [[ $issues_found == "false" ]]; then
      log_success "No issues found with Anki installation"
      exit 0
    fi
  else
    log_error "Anki import test failed"
    issues_found=true
  fi

  if [[ $CHECK_ONLY == "true" ]]; then
    if [[ $issues_found == "true" ]]; then
      echo ""
      log_info "Issues detected. Run without --check to fix."
      exit 1
    fi
    exit 0
  fi

  # Apply fixes
  echo ""
  log_info "Applying fixes..."

  # Check if python-aqtinstall is installed and remove it if nothing depends on it
  if pacman -Qi python-aqtinstall &> /dev/null; then
    local required_by
    required_by=$(pacman -Qi python-aqtinstall | grep "Required By" | cut -d: -f2 | xargs)
    if [[ $required_by == "None" ]]; then
      log_info "Removing python-aqtinstall (conflicts with Anki)..."
      sudo pacman -R --noconfirm python-aqtinstall
    else
      log_warn "python-aqtinstall is required by: $required_by"
      log_warn "Cannot remove automatically. You may need to resolve this manually."
    fi
  fi

  # Rebuild anki package
  if [[ $anki_pkg == "anki-git" ]]; then
    log_info "Rebuilding anki-git for Python $sys_python..."
    yay -S anki-git --rebuild --noconfirm
  elif [[ $anki_pkg == "anki" ]]; then
    log_info "Reinstalling anki..."
    sudo pacman -S anki --noconfirm
  else
    log_warn "Package $anki_pkg may need manual rebuild"
  fi

  # Verify fix
  echo ""
  log_info "Verifying fix..."
  if python -c "from aqt import run" 2> /dev/null; then
    log_success "Anki is now working!"
    echo ""
    echo "You can start Anki with: anki"
  else
    log_error "Fix may not have worked. Please check manually."
    exit 1
  fi
}

main "$@"

#!/bin/bash
#==============================================================================
# Offline Documentation Setup
# Downloads and indexes official documentation for multiple programming languages
#
# Usage: ./setup_offline_docs.sh [--all | --python | --c | --js | --rust | --go]
#
# Documentation is stored in: ~/.local/share/offline-docs/
#==============================================================================

set -e

# Configuration
DOCS_DIR="${OFFLINE_DOCS_DIR:-$HOME/.local/share/offline-docs}"
INDEX_DIR="$DOCS_DIR/.index"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
  echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  $1${NC}"
  echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

print_status() {
  echo -e "${YELLOW}→${NC} $1"
}

print_success() {
  echo -e "${GREEN}✓${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
}

# Create directory structure
setup_dirs() {
  mkdir -p "$DOCS_DIR"/{python,c_cpp,javascript,typescript,rust,go,ruby,java,shell}
  mkdir -p "$INDEX_DIR"
}

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"

# shellcheck source=lib/offline_python.sh
source "$SCRIPT_DIR/lib/offline_python.sh"
# shellcheck source=lib/offline_cpp.sh
source "$SCRIPT_DIR/lib/offline_cpp.sh"
# shellcheck source=lib/offline_js.sh
source "$SCRIPT_DIR/lib/offline_js.sh"
# shellcheck source=lib/offline_rust.sh
source "$SCRIPT_DIR/lib/offline_rust.sh"
# shellcheck source=lib/offline_index.sh
source "$SCRIPT_DIR/lib/offline_index.sh"
# shellcheck source=lib/offline_status.sh
source "$SCRIPT_DIR/lib/offline_status.sh"


main() {
  setup_dirs

  if [ $# -eq 0 ]; then
    usage
    exit 0
  fi

  while [ $# -gt 0 ]; do
    case "$1" in
      --all)
        download_python_docs
        download_cpp_docs
        download_js_docs
        download_rust_docs
        download_go_docs
        download_shell_docs
        setup_zeal_docsets
        ;;
      --python)
        download_python_docs
        ;;
      --cpp | --c | --c++)
        download_cpp_docs
        ;;
      --js | --javascript)
        download_js_docs
        ;;
      --rust)
        download_rust_docs
        ;;
      --go)
        download_go_docs
        ;;
      --shell | --bash)
        download_shell_docs
        ;;
      --zeal)
        setup_zeal_docsets
        ;;
      --status)
        show_status
        ;;
      --help | -h)
        usage
        exit 0
        ;;
      *)
        print_error "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
    shift
  done

  echo ""
  print_header "Setup Complete"
  echo "Documentation stored in: $DOCS_DIR"
  echo ""
  echo "Use 'lookup_docs.sh <term> [language]' to search documentation"
}

main "$@"

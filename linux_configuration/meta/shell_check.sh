#!/usr/bin/env bash

# A one-stop shell linting helper for this repo.
# - Installs shell linters on Arch Linux (shellcheck, shfmt) and optionally via AUR if available
# - Discovers shell scripts in the repository (by extension or shebang)
# - Runs: shellcheck, shfmt (diff mode), optional: checkbashisms, bashate, and shell syntax checks (bash -n, zsh -n, sh/dash -n)
# - Prints a summarized report and returns non-zero if any linter reports issues
#
# Usage:
#   meta/shell_check.sh [--path DIR] [--skip-install] [--install-only] [--list-only] [--verbose]
#
# Notes:
# - Arch install uses pacman: shellcheck shfmt
# - Optional linters if available (installed already or via AUR helper yay/paru): checkbashisms, bashate
# - On non-Arch systems, install is skipped with a helpful hint

set -uo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

# Source common library for log_info, log_warn, log_error
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

DEFAULT_ROOT=$(cd -- "$SCRIPT_DIR/../../" && pwd)

ROOT_DIR="$DEFAULT_ROOT"
SKIP_INSTALL="false"
INSTALL_ONLY="false"
LIST_ONLY="false"
VERBOSE="false"

usage() {
  cat << EOF
Usage: $(basename "$0") [options]

Options:
  --path DIR         Root directory to scan (default: repo root at $DEFAULT_ROOT)
  --skip-install     Skip installing linters
  --install-only     Only install linters, do not scan
  --list-only        Only list discovered shell files, do not run linters
  --verbose          Print additional details while running
  -h, --help         Show this help

Linters used:
	Required: shellcheck, shfmt
	Optional (if available): checkbashisms, bashate
	Syntax checks: bash -n, zsh -n (if installed), sh/dash -n
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      ROOT_DIR="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL="true"
      shift
      ;;
    --install-only)
      INSTALL_ONLY="true"
      shift
      ;;
    --list-only)
      LIST_ONLY="true"
      shift
      ;;
    --verbose)
      VERBOSE="true"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      log_error "Unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ ! -d $ROOT_DIR ]]; then
  log_error "Path not found: $ROOT_DIR"
  exit 2
fi


TMPDIR=$(mktemp -d)
trap 'rm -rf "${TMPDIR:-}"' EXIT

ABS_FILES_Z="$TMPDIR/files_abs.zlist"
REL_FILES_Z="$TMPDIR/files_rel.zlist"

# Sourced after the options and the temp-file paths above, which they read.
source "$SCRIPT_DIR/lib/shell_check_install.sh"
source "$SCRIPT_DIR/lib/shell_check_discover.sh"
source "$SCRIPT_DIR/lib/shell_check_lint.sh"
# Main
if [[ $INSTALL_ONLY == "true" ]]; then
  install_linters
  exit $?
fi

# Only attempt installs if not list-only
if [[ $LIST_ONLY != "true" ]]; then
  install_linters || true
fi

discover_shell_files "$ROOT_DIR"
print_file_list

if [[ $LIST_ONLY == "true" ]]; then
  exit 0
fi

run_linters
exit $?

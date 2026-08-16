#!/usr/bin/env bash
# ==============================================================================
# Python Linting Script - Run ALL linters with aggressive settings
# ==============================================================================
# Usage:
#   ./lint_python.sh              # Lint all Python files
#   ./lint_python.sh --fix        # Lint and auto-fix where possible
#   ./lint_python.sh <file.py>    # Lint specific file
#   ./lint_python.sh --quick      # Quick lint (ruff + mypy only)
#   ./lint_python.sh --report     # Generate detailed reports
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
# readlink -f, not a bare dirname: the repo root carries a lint_python.sh
# symlink into meta/, and `dirname` on the symlink path yields the repo root,
# where lib/ does not exist. That made `./lint_python.sh` die on the source
# line below.
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="${SCRIPT_DIR}"

# Sourced before argument parsing: --help calls usage() from here.
# shellcheck source=./lib/lint_output.sh
source "${SCRIPT_DIR}/lib/lint_output.sh"
PYTHON_PATHS=(
	"PYTHON"
	"articles"
	"poker-modifier-app"
	"tests"
)
EXCLUDE_PATHS=(
	".venv"
	"__pycache__"
	".git"
	"Bash/ffmpeg-build"
	".pytest_cache"
	".ruff_cache"
	".mypy_cache"
)

# Build exclude pattern for find
EXCLUDE_PATTERN=""
for path in "${EXCLUDE_PATHS[@]}"; do
	EXCLUDE_PATTERN="${EXCLUDE_PATTERN} -path '*/${path}/*' -prune -o"
done

# Parse arguments
FIX_MODE=false
QUICK_MODE=false
REPORT_MODE=false
# Kept as BOTH a string and an array on purpose: run_tool() takes a single
# command STRING (it evals it), so the string form has to stay, while the
# handful of direct invocations below need proper argument splitting that
# only an array gives -- an unquoted "${TARGET_FILES}" there would also glob.
TARGET_FILES=""
TARGET_FILES_ARR=()

while [[ $# -gt 0 ]]; do
	case $1 in
	--fix | -f)
		FIX_MODE=true
		shift
		;;
	--quick | -q)
		QUICK_MODE=true
		shift
		;;
	--report | -r)
		REPORT_MODE=true
		shift
		;;
	--help | -h)
		usage "$0"
		exit 0
		;;
	*)
		TARGET_FILES="${TARGET_FILES} $1"
		TARGET_FILES_ARR+=("$1")
		shift
		;;
	esac
done

# If no target specified, use default paths
if [[ -z "${TARGET_FILES}" ]]; then
	TARGET_FILES="${PYTHON_PATHS[*]}"
	TARGET_FILES_ARR=("${PYTHON_PATHS[@]}")
fi

# Create reports directory if needed
if [[ "${REPORT_MODE}" == true ]]; then
	mkdir -p "${PROJECT_ROOT}/lint-reports"
fi

# Track overall status
OVERALL_STATUS=0
FAILED_TOOLS=()

# ==============================================================================
# Main linting process
# ==============================================================================

print_header "Python Linting Suite - Aggressive Mode"
echo ""
print_info "Target: ${TARGET_FILES}"
print_info "Fix mode: ${FIX_MODE}"
print_info "Quick mode: ${QUICK_MODE}"
print_info "Report mode: ${REPORT_MODE}"

cd "${PROJECT_ROOT}"

# ==============================================================================
# RUFF - Primary linter and formatter
# ==============================================================================
if check_tool ruff; then
	if [[ "${FIX_MODE}" == true ]]; then
		run_tool "ruff-lint" "ruff check --fix --show-fixes ${TARGET_FILES}" || OVERALL_STATUS=1
		run_tool "ruff-format" "ruff format ${TARGET_FILES}" || OVERALL_STATUS=1
	else
		run_tool "ruff-lint" "ruff check ${TARGET_FILES}" || OVERALL_STATUS=1
		run_tool "ruff-format-check" "ruff format --check ${TARGET_FILES}" || OVERALL_STATUS=1
	fi
fi

# ==============================================================================
# MYPY - Static type checking
# ==============================================================================
if check_tool mypy; then
	run_tool "mypy" "mypy --strict --ignore-missing-imports ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# Quick mode exits here
if [[ "${QUICK_MODE}" == true ]]; then
	print_header "Quick Lint Complete"
	if [[ ${#FAILED_TOOLS[@]} -gt 0 ]]; then
		print_error "Failed tools: ${FAILED_TOOLS[*]}"
		exit 1
	else
		print_success "All quick checks passed!"
		exit 0
	fi
fi

# shellcheck source=./lib/lint_full_tools.sh
source "${SCRIPT_DIR}/lib/lint_full_tools.sh"
run_full_mode_linters

# ==============================================================================
# Summary
# ==============================================================================
print_header "Linting Summary"
echo ""

if [[ ${OVERALL_STATUS} -ne 0 ]]; then
	print_error "The following tools reported issues:"
	for tool in "${FAILED_TOOLS[@]}"; do
		echo "  - ${tool}"
	done
	echo ""
	if [[ "${REPORT_MODE}" == true ]]; then
		print_info "Detailed reports saved to: ${PROJECT_ROOT}/lint-reports/"
	fi
	print_info "Run with --fix to auto-fix issues where possible"
	exit "${OVERALL_STATUS}"
else
	print_success "All linting checks passed!"
	exit 0
fi

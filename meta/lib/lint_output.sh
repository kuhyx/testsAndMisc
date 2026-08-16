#!/bin/bash

# ==============================================================================
# Output formatting and tool-running helpers for lint_python.sh.
#
# Split out to keep the entry script under the 250-line cap. The seam passes
# state: run_tool appends to the caller's FAILED_TOOLS array and reads
# REPORT_MODE and PROJECT_ROOT, all of which lint_python.sh defines before
# sourcing this file. The colour variables come from the caller too.
# ==============================================================================

# shellcheck shell=bash

usage() {
	echo "Usage: $1 [OPTIONS] [FILES...]"
	echo ""
	echo "Options:"
	echo "  --fix, -f      Auto-fix issues where possible"
	echo "  --quick, -q    Quick mode (ruff + mypy only)"
	echo "  --report, -r   Generate detailed reports to ./lint-reports/"
	echo "  --help, -h     Show this help message"
	echo ""
	echo "Examples:"
	echo "  $1                    # Lint all Python files"
	echo "  $1 --fix              # Lint and auto-fix"
	echo "  $1 PYTHON/            # Lint specific directory"
	echo "  $1 --quick --fix      # Quick lint with auto-fix"
}

print_header() {
	echo ""
	echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
	echo -e "${BOLD}${BLUE}  $1${NC}"
	echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
}

print_subheader() {
	echo ""
	echo -e "${CYAN}──────────────────────────────────────────────────────────────${NC}"
	echo -e "${CYAN}  $1${NC}"
	echo -e "${CYAN}──────────────────────────────────────────────────────────────${NC}"
}

print_success() {
	echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
	echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
	echo -e "${RED}✗${NC} $1"
}

print_info() {
	echo -e "${BLUE}ℹ${NC} $1"
}

run_tool() {
	local tool_name="$1"
	local tool_cmd="$2"
	local report_file="${PROJECT_ROOT}/lint-reports/${tool_name}.txt"

	print_subheader "Running ${tool_name}..."

	if [[ "${REPORT_MODE}" == true ]]; then
		if eval "${tool_cmd}" 2>&1 | tee "${report_file}"; then
			print_success "${tool_name} passed"
			return 0
		else
			print_error "${tool_name} found issues (see ${report_file})"
			FAILED_TOOLS+=("${tool_name}")
			return 1
		fi
	else
		if eval "${tool_cmd}"; then
			print_success "${tool_name} passed"
			return 0
		else
			print_error "${tool_name} found issues"
			FAILED_TOOLS+=("${tool_name}")
			return 1
		fi
	fi
}

check_tool() {
	if command -v "$1" &>/dev/null; then
		return 0
	else
		print_warning "$1 not found, skipping..."
		return 1
	fi
}

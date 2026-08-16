#!/usr/bin/env bash
#==============================================================================
# repo_to_study.sh - Complete pipeline: Repo → Analysis → Offline Docs → Study Materials
#
# Usage:
#   repo_to_study.sh <repo_url_or_path>
#
# Examples:
#   repo_to_study.sh https://github.com/user/repo
#   repo_to_study.sh /path/to/local/repo
#   repo_to_study.sh .
#
# Output:
#   Creates study materials in ~/.local/share/study-materials/<repo_name>/
#   - documentation_links.md (with offline doc paths)
#   - anki_cards.txt (importable to Anki)
#   - llm_anki_prompt.md (for generating more cards with AI)
#==============================================================================

set -euo pipefail

# Script directory for finding other tools
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZE_SCRIPT="$SCRIPT_DIR/analyze_repo.sh"
STUDY_SCRIPT="$SCRIPT_DIR/generate_study_materials.sh"
SETUP_DOCS_SCRIPT="$SCRIPT_DIR/setup_offline_docs.sh"

# Default output location (not in script dir, user's data dir)
STUDY_MATERIALS_BASE="$HOME/.local/share/study-materials"

# Work directories
WORK_DIR="/tmp/repo_study_$$"
# shellcheck disable=SC2034  # OUTPUT_DIR set dynamically by parse_args
OUTPUT_DIR=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

#==============================================================================
# Helper Functions (all print to stderr to not interfere with return values)
#==============================================================================
print_header() {
	echo -e "\n${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}" >&2
	echo -e "${BOLD}${CYAN}  $1${NC}" >&2
	echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}\n" >&2
}

print_step() {
	echo -e "${BOLD}${BLUE}▶ $1${NC}" >&2
}

print_success() {
	echo -e "${GREEN}✓ $1${NC}" >&2
}

print_error() {
	echo -e "${RED}✗ $1${NC}" >&2
}

print_info() {
	echo -e "${YELLOW}→ $1${NC}" >&2
}

cleanup() {
	if [ -d "$WORK_DIR" ] && [ "$WORK_DIR" != "/" ]; then
		rm -rf "$WORK_DIR"
	fi
}

trap cleanup EXIT

usage() {
	cat <<EOF
repo_to_study.sh - Generate study materials from any repository

USAGE:
    $(basename "$0") <repo_url_or_path> [output_dir]

ARGUMENTS:
    repo_url_or_path    Git URL (https/ssh) or local path to repository
    output_dir          Optional: where to save results
                        Default: ~/.local/share/study-materials/<repo_name>/

EXAMPLES:
    $(basename "$0") https://github.com/python/cpython
    $(basename "$0") git@github.com:torvalds/linux.git
    $(basename "$0") /home/user/my-project
    $(basename "$0") . ~/notes/my_study_notes

OUTPUT FILES:
    documentation_links.md  - Markdown with offline documentation links
    anki_cards.txt          - Tab-separated file for Anki import
    llm_anki_prompt.md      - Prompt template for AI-generated cards
    analysis/               - Raw analysis data (imports, keywords, functions)

EOF
	exit 0
}

# shellcheck source=lib/repo_study_steps.sh
source "$SCRIPT_DIR/lib/repo_study_steps.sh"

main() {
	# Handle help
	if [ $# -lt 1 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
		usage
	fi

	local input="$1"
	local output_dir="${2:-}" # Will be set after we know repo name

	print_header "Repo → Study Materials Pipeline"

	# Setup
	mkdir -p "$WORK_DIR"
	check_dependencies
	ensure_offline_docs

	# Step 1: Get repository
	print_header "Step 1/3: Getting Repository"
	local repo_path
	repo_path=$(get_repo "$input")

	# Extract repo name from path (since get_repo runs in subshell, REPO_NAME is lost)
	if [ -z "$REPO_NAME" ]; then
		REPO_NAME=$(basename "$repo_path")
	fi

	# Set default output dir based on repo name
	if [ -z "$output_dir" ]; then
		output_dir="$STUDY_MATERIALS_BASE/$REPO_NAME"
	elif [[ $output_dir != /* ]]; then
		# Convert relative to absolute
		output_dir="$(pwd)/$output_dir"
	fi

	echo -e "${BOLD}Input:${NC}  $input" >&2
	echo -e "${BOLD}Output:${NC} $output_dir" >&2
	echo "" >&2

	# Step 2: Analyze
	print_header "Step 2/3: Analyzing Code"
	local analysis_dir
	analysis_dir=$(analyze_repo "$repo_path")

	# Step 3: Generate materials
	print_header "Step 3/3: Generating Study Materials"
	generate_materials "$analysis_dir" "$output_dir"

	# Show results
	show_summary "$output_dir"
}

main "$@"

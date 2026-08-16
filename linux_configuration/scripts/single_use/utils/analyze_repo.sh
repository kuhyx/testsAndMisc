#!/bin/bash
# Analyze a git repository for most-used keywords, functions, etc.
# Usage: ./analyze_repo.sh [repo_url_or_local_path] [output_dir] [--no-ignore]
#
# Examples:
#   ./analyze_repo.sh https://github.com/torvalds/linux    # Clone from URL
#   ./analyze_repo.sh /path/to/local/repo                  # Use local directory
#   ./analyze_repo.sh .                                    # Analyze current directory
#   ./analyze_repo.sh . /tmp/out --no-ignore               # Include node_modules, etc.

set -e

# Resolve this script's directory up front (absolute), before any cd, so sibling
# helpers like fast_count.py remain locatable once we cd into the analyzed repo.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
INPUT=""
WORK_DIR=""
RESPECT_GITIGNORE=true

for arg in "$@"; do
	case "$arg" in
	--no-ignore)
		RESPECT_GITIGNORE=false
		;;
	*)
		if [ -z "$INPUT" ]; then
			INPUT="$arg"
		elif [ -z "$WORK_DIR" ]; then
			WORK_DIR="$arg"
		fi
		;;
	esac
done

INPUT="${INPUT:-https://github.com/torvalds/linux}"
WORK_DIR="${WORK_DIR:-/tmp/repo_analysis}"
TOP_N=50 # Number of top results to show

# Directories to exclude (unless --no-ignore is used)
EXCLUDE_DIRS="node_modules|\.git|vendor|\.venv|venv|__pycache__|\.cache|build|dist|\.next|\.nuxt|target|\.tox|\.eggs"

# Detect if input is a URL or local path
is_url() {
	[[ $1 =~ ^https?:// ]] || [[ $1 =~ ^git@ ]] || [[ $1 =~ ^ssh:// ]]
}

IS_LOCAL=false
if is_url "$INPUT"; then
	REPO_URL="$INPUT"
	REPO_NAME=$(basename "$REPO_URL" .git)
	REPO_DIR="$WORK_DIR/$REPO_NAME"
else
	# Local path - resolve to absolute path
	IS_LOCAL=true
	if [ -d "$INPUT" ]; then
		REPO_DIR=$(cd "$INPUT" && pwd)
		REPO_NAME=$(basename "$REPO_DIR")
	else
		echo "Error: '$INPUT' is not a valid directory or URL"
		exit 1
	fi
fi

RESULTS_DIR="$WORK_DIR/results_${REPO_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


#==============================================================================
# Libraries
#==============================================================================
# Sourced after the colour constants and configuration above, which they read.
source "$SCRIPT_DIR/lib/analyze_repo_scan.sh"
source "$SCRIPT_DIR/lib/analyze_repo_tools.sh"
source "$SCRIPT_DIR/lib/analyze_repo_separate.sh"
source "$SCRIPT_DIR/lib/analyze_repo_report.sh"
source "$SCRIPT_DIR/lib/analyze_repo_symbols.sh"

#==============================================================================
# STEP 0: Install Missing Tools
#==============================================================================
print_header "STEP 0: Checking/Installing Required Tools"
install_missing_tools

# Create directories
mkdir -p "$WORK_DIR" "$RESULTS_DIR"

# STEP 1: Clone or Use Local Repository
#==============================================================================
print_header "STEP 1: Repository Setup"

if [ "$IS_LOCAL" = true ]; then
	echo "Using local repository: $REPO_DIR"
	if [ ! -d "$REPO_DIR" ]; then
		echo "Error: Directory does not exist: $REPO_DIR"
		exit 1
	fi
else
	# Remote URL - clone it
	if [ -d "$REPO_DIR" ]; then
		echo "Repository already exists at $REPO_DIR"
		echo "Updating..."
		cd "$REPO_DIR"
		git pull --depth 1 2>/dev/null || echo "Update skipped (shallow clone)"
	else
		echo "Cloning $REPO_URL (shallow clone for speed)..."
		git clone --depth 1 "$REPO_URL" "$REPO_DIR"
	fi
fi

cd "$REPO_DIR"
echo "Repository: $REPO_NAME"
echo "Location: $REPO_DIR"
echo "Repository size: $(du -sh . | cut -f1)"
if [ "$RESPECT_GITIGNORE" = true ] && is_git_repo; then
	# Count files respecting .gitignore
	FILE_COUNT=$({
		git ls-files 2>/dev/null
		git ls-files --others --exclude-standard 2>/dev/null
	} | sort -u | wc -l)
	echo "Files: $FILE_COUNT (respecting .gitignore)"
elif [ "$RESPECT_GITIGNORE" = true ]; then
	echo "Files: $(find . -type f 2>/dev/null | grep -cEv "/($EXCLUDE_DIRS)/") (excluding common dirs)"
else
	echo "Files: $(find . -type f | wc -l)"
fi

#==============================================================================
# STEP 2: Basic Statistics with tokei
#==============================================================================
print_header "STEP 2: Code Statistics with tokei"

echo "Running tokei..."
tokei . | tee "$RESULTS_DIR/tokei_stats.txt"

#==============================================================================
# STEP 3: Code Statistics with scc
#==============================================================================
print_header "STEP 3: Code Statistics with scc (includes complexity)"

echo "Running scc..."
scc . | tee "$RESULTS_DIR/scc_stats.txt"

print_subheader "Top 10 Most Complex Files"
scc --by-file --sort complexity . 2>/dev/null | head -20 | tee "$RESULTS_DIR/scc_complexity.txt"

#==============================================================================
# STEP 4: Fast Keyword Analysis (Code vs Comments) - Multi-Language
#==============================================================================
print_header "STEP 4: Fast Keyword Analysis (Code vs Comments)"

detect_languages

#------------------------------------------------------------------------------
# Multi-language comment processing - KEEP LANGUAGES SEPARATE
#------------------------------------------------------------------------------
print_subheader "Processing source files (separating code from comments)..."

COMMENTS_TEMP=$(mktemp)
trap 'rm -f "$COMMENTS_TEMP" /tmp/code_*.tmp 2>/dev/null' EXIT
declare -A LANG_CODE_FILES

separate_code_and_comments LANG_CODE_FILES "$COMMENTS_TEMP"
report_languages LANG_CODE_FILES "$COMMENTS_TEMP"

#==============================================================================
# STEP 5: ctags Symbol Analysis
#==============================================================================
analyze_symbols

#==============================================================================
# STEP 6: cscope Analysis
#==============================================================================
print_header "STEP 6: cscope Database Analysis"
analyze_cscope

#==============================================================================
# STEP 7: clang AST Analysis (if available)
#==============================================================================
print_header "STEP 7: clang-based Analysis (AST-level)"
analyze_clang_ast

#==============================================================================
# STEP 8: Summary
#==============================================================================
print_header "ANALYSIS COMPLETE"

echo "Results saved to: $RESULTS_DIR/"
echo ""
ls -la "$RESULTS_DIR/"

echo ""
echo -e "${GREEN}Quick Summary:${NC}"
echo ""

if [ -f "$RESULTS_DIR/grep_keywords.txt" ]; then
	echo "Top 5 Language Keywords (in code):"
	head -5 "$RESULTS_DIR/grep_keywords.txt" | awk '{printf "  %s: %s times\n", $2, $1}'
fi

echo ""
if [ -f "$RESULTS_DIR/grep_function_calls.txt" ]; then
	echo "Top 5 Function/Method Calls (in code):"
	head -5 "$RESULTS_DIR/grep_function_calls.txt" | awk '{printf "  %s(): %s times\n", $2, $1}'
fi

echo ""
if [ -f "$RESULTS_DIR/comment_words.txt" ]; then
	echo "Top 5 Words in Comments:"
	head -5 "$RESULTS_DIR/comment_words.txt" | awk '{printf "  %s: %s times\n", $2, $1}'
fi

echo ""
if [ -f "$RESULTS_DIR/grep_imports.txt" ]; then
	echo "Top 5 Imports/Includes:"
	head -5 "$RESULTS_DIR/grep_imports.txt" | awk '{count=$1; $1=""; printf "  %s: %s times\n", substr($0,2), count}'
fi

echo ""
echo -e "${BLUE}To explore interactively with cscope (C/C++ only):${NC}"
echo "  cd $REPO_DIR && cscope -d -f $RESULTS_DIR/cscope.out"
echo ""
echo -e "${BLUE}To browse tags in vim:${NC}"
echo "  cd $REPO_DIR && vim -t main"

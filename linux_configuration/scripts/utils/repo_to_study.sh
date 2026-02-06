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
  cat << EOF
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

#==============================================================================
# Check Dependencies
#==============================================================================
check_dependencies() {
  local missing=()

  # Check for required scripts
  if [ ! -x "$ANALYZE_SCRIPT" ]; then
    missing+=("analyze_repo.sh not found at $ANALYZE_SCRIPT")
  fi

  if [ ! -x "$STUDY_SCRIPT" ]; then
    missing+=("generate_study_materials.sh not found at $STUDY_SCRIPT")
  fi

  # Check for basic tools
  for cmd in git curl grep sed awk; do
    if ! command -v "$cmd" &> /dev/null; then
      missing+=("$cmd")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    print_error "Missing dependencies:"
    for dep in "${missing[@]}"; do
      echo "  - $dep"
    done
    exit 1
  fi
}

#==============================================================================
# Ensure Offline Docs are Available
#==============================================================================
ensure_offline_docs() {
  local docs_dir="$HOME/.local/share/offline-docs"

  if [ ! -d "$docs_dir/python" ]; then
    print_info "Offline docs not found. Setting up Python documentation..."
    if [ -x "$SETUP_DOCS_SCRIPT" ]; then
      "$SETUP_DOCS_SCRIPT" --python
    else
      print_info "Run setup_offline_docs.sh --all to enable offline documentation"
    fi
  fi
}

# Global to store repo name for cloned repos
REPO_NAME=""

#==============================================================================
# Get Repository
#==============================================================================
get_repo() {
  local input="$1"
  local repo_dir=""

  # Check if it's a URL (git clone needed)
  if [[ $input =~ ^https?:// ]] || [[ $input =~ ^git@ ]]; then
    print_step "Cloning repository..."

    # Extract repo name from URL
    REPO_NAME=$(basename "$input" .git)
    repo_dir="$WORK_DIR/$REPO_NAME"
    mkdir -p "$WORK_DIR"

    if git clone --depth 1 "$input" "$repo_dir" >&2 2>&1; then
      print_success "Cloned: $input"
    else
      print_error "Failed to clone repository"
      exit 1
    fi

    echo "$repo_dir"
  # Local path
  elif [ -d "$input" ]; then
    # Convert to absolute path
    repo_dir="$(cd "$input" && pwd)"
    REPO_NAME=$(basename "$repo_dir")
    print_success "Using local repository: $repo_dir"
    echo "$repo_dir"
  else
    print_error "Invalid input: '$input' is not a valid URL or directory"
    exit 1
  fi
}

#==============================================================================
# Analyze Repository
#==============================================================================
analyze_repo() {
  local repo_path="$1"
  local repo_name="$REPO_NAME"
  [ -z "$repo_name" ] && repo_name=$(basename "$repo_path")

  print_step "Analyzing repository..."

  # Run the analyzer (it outputs to stderr/stdout, results go to /tmp/repo_analysis/)
  "$ANALYZE_SCRIPT" "$repo_path" >&2 || true

  # Find the results directory
  local results_dir="/tmp/repo_analysis/results_${repo_name}"
  if [ ! -d "$results_dir" ]; then
    # Try without prefix
    results_dir="/tmp/repo_analysis/results"
  fi

  if [ ! -d "$results_dir" ] || [ ! -d "$results_dir/per_language" ]; then
    print_error "Could not find analysis results at $results_dir"
    exit 1
  fi

  print_success "Analysis complete: $results_dir"
  echo "$results_dir"
}

#==============================================================================
# Generate Study Materials
#==============================================================================
generate_materials() {
  local analysis_dir="$1"
  local output_dir="$2"

  print_step "Generating study materials with offline documentation..."

  # Run study materials generator
  cd "$analysis_dir"
  if "$STUDY_SCRIPT" . 2> /dev/null | grep -E "^(Created|✓|Files created)" | head -5; then
    print_success "Study materials generated"
  else
    # Try anyway, might have succeeded
    true
  fi

  # Create output directory and copy results
  mkdir -p "$output_dir"

  # Copy generated files
  [ -f "documentation_links.md" ] && cp "documentation_links.md" "$output_dir/"
  [ -f "anki_cards.txt" ] && cp "anki_cards.txt" "$output_dir/"
  [ -f "llm_anki_prompt.md" ] && cp "llm_anki_prompt.md" "$output_dir/"

  # Copy analysis data
  mkdir -p "$output_dir/analysis"
  [ -d "per_language" ] && cp -r "per_language" "$output_dir/analysis/"
  [ -f "grep_imports.txt" ] && cp "grep_imports.txt" "$output_dir/analysis/"
  [ -f "grep_keywords.txt" ] && cp "grep_keywords.txt" "$output_dir/analysis/"
  [ -f "grep_function_calls.txt" ] && cp "grep_function_calls.txt" "$output_dir/analysis/"

  print_success "Files saved to: $output_dir"
}

#==============================================================================
# Show Summary
#==============================================================================
show_summary() {
  local output_dir="$1"

  print_header "Study Materials Ready!"

  echo -e "${BOLD}Output directory:${NC} $output_dir"
  echo ""
  echo -e "${BOLD}Generated files:${NC}"

  if [ -f "$output_dir/documentation_links.md" ]; then
    local doc_lines
    doc_lines=$(wc -l < "$output_dir/documentation_links.md")
    echo -e "  📚 ${GREEN}documentation_links.md${NC} ($doc_lines lines)"
    echo "     Contains links to OFFLINE documentation"
  fi

  if [ -f "$output_dir/anki_cards.txt" ]; then
    local card_count
    card_count=$(grep -c $'^\w' "$output_dir/anki_cards.txt" 2> /dev/null || echo "0")
    echo -e "  🎴 ${GREEN}anki_cards.txt${NC} (~$card_count cards)"
    echo "     Import to Anki: File → Import → Tab separated"
  fi

  if [ -f "$output_dir/llm_anki_prompt.md" ]; then
    echo -e "  🤖 ${GREEN}llm_anki_prompt.md${NC}"
    echo "     Use with ChatGPT/Claude to generate more cards"
  fi

  if [ -d "$output_dir/analysis" ]; then
    echo -e "  📊 ${GREEN}analysis/${NC}"
    echo "     Raw analysis data (imports, keywords, functions per language)"
  fi

  echo ""
  echo -e "${BOLD}Quick preview of imports with offline docs:${NC}"
  if [ -f "$output_dir/documentation_links.md" ]; then
    grep -A20 "import/from" "$output_dir/documentation_links.md" 2> /dev/null |
      grep "^\| \`" | head -5 |
      sed 's/|/│/g'
  fi

  echo ""
  echo -e "${BOLD}Next steps:${NC}"
  echo "  1. Open documentation_links.md to browse offline docs"
  echo "  2. Import anki_cards.txt into Anki for spaced repetition"
  echo "  3. Use llm_anki_prompt.md to generate more targeted cards"
  echo ""
  echo -e "${CYAN}To view a doc:${NC} xdg-open 'file:///path/from/documentation_links.md'"
}

#==============================================================================
# Main
#==============================================================================
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

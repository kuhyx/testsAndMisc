#!/bin/bash
# Generate study materials (documentation links + Anki cards) from repo analysis
# Usage: ./generate_study_materials.sh <results_dir> [--top N] [--languages "python,c,js"]
#
# Examples:
#   ./generate_study_materials.sh /tmp/repo_analysis/results_myproject
#   ./generate_study_materials.sh /tmp/repo_analysis/results_linux --top 20 --languages "c"
#   ./generate_study_materials.sh ./results --languages "python,typescript"

set -e

# Each generation phase and each family of doc-URL builders lives in a lib
# beside this file; this script keeps the configuration, the argument
# parsing and the order the phases run in.
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib"
# shellcheck source=lib/study_doc_urls.sh
. "$LIB_DIR/study_doc_urls.sh"
# shellcheck source=lib/study_doc_urls_more.sh
. "$LIB_DIR/study_doc_urls_more.sh"
# shellcheck source=lib/study_doc_lookup.sh
. "$LIB_DIR/study_doc_lookup.sh"
# shellcheck source=lib/study_gen_docs.sh
. "$LIB_DIR/study_gen_docs.sh"
# shellcheck source=lib/study_gen_anki.sh
. "$LIB_DIR/study_gen_anki.sh"
# shellcheck source=lib/study_gen_llm.sh
. "$LIB_DIR/study_gen_llm.sh"

#==============================================================================
# Configuration
#==============================================================================
RESULTS_DIR="${1:-.}"
TOP_N=30
LANGUAGES="auto" # Will detect from results

# Parse arguments
shift || true
while [[ $# -gt 0 ]]; do
	case "$1" in
	--top)
		TOP_N="$2"
		shift 2
		;;
	--languages)
		LANGUAGES="$2"
		shift 2
		;;
	*)
		shift
		;;
	esac
done

# Output files
DOCS_FILE="$RESULTS_DIR/documentation_links.md"
ANKI_FILE="$RESULTS_DIR/anki_cards.txt"
LLM_PROMPT_FILE="$RESULTS_DIR/llm_anki_prompt.md"

# Offline documentation setup
OFFLINE_DOCS_DIR="${OFFLINE_DOCS_DIR:-$HOME/.local/share/offline-docs}"
LOOKUP_SCRIPT="$(dirname "$0")/lookup_docs.sh"
USE_OFFLINE_DOCS=false

# Check if offline docs are available
if [ -d "$OFFLINE_DOCS_DIR" ] && [ -x "$LOOKUP_SCRIPT" ]; then
	USE_OFFLINE_DOCS=true
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

#==============================================================================
# Documentation URL Generators (online fallback)
#==============================================================================

#==============================================================================
# Main Processing
#==============================================================================

# Check if results directory exists
if [ ! -d "$RESULTS_DIR" ]; then
	echo -e "${RED}Error: Results directory not found: $RESULTS_DIR${NC}"
	echo "Run analyze_repo.sh first to generate analysis results."
	exit 1
fi

# Detect or use specified language
if [ "$LANGUAGES" = "auto" ]; then
	PRIMARY_LANG=$(detect_language)
	echo -e "${BLUE}Detected primary language: ${GREEN}$PRIMARY_LANG${NC}"
else
	PRIMARY_LANG=$(echo "$LANGUAGES" | cut -d',' -f1)
	echo -e "${BLUE}Using specified language: ${GREEN}$PRIMARY_LANG${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Generating Study Materials${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
# Patch for generate_study_materials.sh - use per-language files

# The three generation phases, in the order their outputs reference each
# other. Defined above and called here so the file can be split into libs.
generate_doc_links
generate_anki_cards
generate_llm_prompt

#==============================================================================
# Summary
#==============================================================================
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Study Materials Generated!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Files created:"
echo "  📚 Documentation Links: $DOCS_FILE"
echo "  🎴 Anki Cards:          $ANKI_FILE"
echo "  🤖 LLM Prompt:          $LLM_PROMPT_FILE"
echo ""
echo "Next steps:"
echo "  1. Review documentation_links.md for learning resources"
echo "  2. Import anki_cards.txt into Anki (File -> Import)"
echo "  3. Use llm_anki_prompt.md with ChatGPT/Claude to generate more cards"
echo ""
echo "Anki import settings:"
echo "  - Field separator: Tab"
echo "  - Allow HTML: Yes"
echo "  - Tags are in last field: Yes"

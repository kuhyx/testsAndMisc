#!/bin/bash
#==============================================================================
# Offline Documentation Lookup
# Searches downloaded documentation for terms
#
# Usage: ./lookup_docs.sh <term> [language] [--open] [--extract]
#
# Examples:
#   ./lookup_docs.sh Path python          # Find Path in Python docs
#   ./lookup_docs.sh vector c_cpp         # Find vector in C++ docs
#   ./lookup_docs.sh map                  # Find map in all languages
#   ./lookup_docs.sh --batch imports.txt  # Lookup multiple terms from file
#==============================================================================

set -e

# Configuration
DOCS_DIR="${OFFLINE_DOCS_DIR:-$HOME/.local/share/offline-docs}"
INDEX_DIR="$DOCS_DIR/.index"

# Colors - only use if stdout is a terminal
if [ -t 1 ]; then
	RED='\033[0;31m'
	GREEN='\033[0;32m'
	BLUE='\033[0;34m'
	YELLOW='\033[1;33m'
	CYAN='\033[0;36m'
	NC='\033[0m'
else
	RED=''
	GREEN=''
	BLUE=''
	YELLOW=''
	CYAN=''
	NC=''
fi

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"

# shellcheck source=lib/docs_python_keywords.sh
source "$SCRIPT_DIR/lib/docs_python_keywords.sh"
# shellcheck source=lib/docs_python.sh
source "$SCRIPT_DIR/lib/docs_python.sh"
# shellcheck source=lib/docs_cpp.sh
source "$SCRIPT_DIR/lib/docs_cpp.sh"
# shellcheck source=lib/docs_js.sh
source "$SCRIPT_DIR/lib/docs_js.sh"
# shellcheck source=lib/docs_rust.sh
source "$SCRIPT_DIR/lib/docs_rust.sh"
# shellcheck source=lib/docs_all.sh
source "$SCRIPT_DIR/lib/docs_all.sh"



main() {
	if [ $# -eq 0 ]; then
		usage
		exit 0
	fi

	local term=""
	local lang=""
	local action="lookup"
	local open_file=false
	local extract=false

	while [ $# -gt 0 ]; do
		case "$1" in
		--open)
			open_file=true
			shift
			;;
		--extract)
			extract=true
			shift
			;;
		--import)
			action="import"
			shift
			term="$1"
			shift
			;;
		--batch)
			action="batch"
			shift
			term="$1" # This is the file
			shift
			;;
		--help | -h)
			usage
			exit 0
			;;
		python | cpp | c_cpp | c | js | javascript | ts | typescript | tsx | jsx | rust | go | shell | bash | all)
			lang="$1"
			shift
			;;
		*)
			if [ -z "$term" ]; then
				term="$1"
			fi
			shift
			;;
		esac
	done

	# Normalize language
	case "$lang" in
	c) lang="cpp" ;;
	javascript | js | typescript | ts | jsx | tsx) lang="js" ;;
	bash) lang="shell" ;;
	"") lang="all" ;;
	esac

	case "$action" in
	lookup)
		if [ "$lang" = "all" ]; then
			lookup_all "$term"
		else
			result=$("lookup_$lang" "$term" 2>/dev/null)
			if [ -n "$result" ]; then
				local file desc
				file=$(echo "$result" | cut -d'|' -f1)
				desc=$(echo "$result" | cut -d'|' -f2)

				echo -e "${GREEN}Found:${NC} $desc"
				echo -e "${BLUE}File:${NC} $file"

				if $extract; then
					echo ""
					echo -e "${YELLOW}--- Content ---${NC}"
					extract_doc_content "$file" "$term"
				fi

				if $open_file && [ -f "$file" ]; then
					xdg-open "$file" 2>/dev/null &
				fi
			else
				echo -e "${RED}Not found:${NC} $term in $lang documentation"
			fi
		fi
		;;

	import)
		result=$(lookup_import "$term" "$lang")
		if [ -n "$result" ]; then
			echo -e "${GREEN}Import lookup:${NC} $term"
			echo "$result"
		else
			echo -e "${RED}Could not parse import:${NC} $term"
		fi
		;;

	batch)
		if [ ! -f "$term" ]; then
			echo "File not found: $term"
			exit 1
		fi

		while IFS= read -r line || [ -n "$line" ]; do
			[ -z "$line" ] && continue
			[[ $line =~ ^# ]] && continue

			echo -e "${CYAN}Looking up:${NC} $line"
			lookup_import "$line" "$lang"
			echo ""
		done <"$term"
		;;
	esac
}

main "$@"

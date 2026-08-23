#!/bin/bash
# Cross-language lookup and content extraction.
#
# Sourced by lookup_docs.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

#==============================================================================
# Generic lookup (searches all languages)
#==============================================================================
lookup_all() {
	local term="$1"

	# Try each language
	for lang in python cpp js rust go shell; do
		local result
		result=$(lookup_$lang "$term" 2>/dev/null)
		if [ -n "$result" ]; then
			echo "$lang: $result"
		fi
	done
}

#==============================================================================
# Parse Python import and lookup the actual imported item
#==============================================================================
parse_python_import() {
	local import_line="$1"

	# Handle "from X import Y" format
	if [[ $import_line =~ ^from[[:space:]]+([^[:space:]]+)[[:space:]]+import[[:space:]]+(.+) ]]; then
		local module="${BASH_REMATCH[1]}"
		local items="${BASH_REMATCH[2]}"

		# Clean up items (remove parentheses, commas, etc.)
		items=$(echo "$items" | sed 's/[(),]//g' | awk '{print $1}')

		# Output: module and first imported item
		echo "$module|$items"
		return 0
	fi

	# Handle "import X" format
	if [[ $import_line =~ ^import[[:space:]]+([^[:space:],]+) ]]; then
		local module="${BASH_REMATCH[1]}"
		echo "$module|"
		return 0
	fi

	return 1
}

#==============================================================================
# Smart lookup for imports
#==============================================================================
lookup_import() {
	local import_line="$1"
	local lang="$2"

	case "$lang" in
	python)
		local parsed
		parsed=$(parse_python_import "$import_line")
		if [ -n "$parsed" ]; then
			local module item
			module=$(echo "$parsed" | cut -d'|' -f1)
			item=$(echo "$parsed" | cut -d'|' -f2)

			# For "from X import Y", look up Y within module X's documentation
			if [ -n "$item" ] && [ -n "$module" ]; then
				local result
				# Pass both item and module to lookup_python
				result=$(lookup_python "$item" "$module")
				if [ -n "$result" ]; then
					echo "$result"
					return 0
				fi
			fi

			# Fall back to module documentation
			lookup_python "$module"
		fi
		;;

	c_cpp)
		# Extract header name from #include <header> or #include "header"
		local header
		header=$(echo "$import_line" | sed -E 's/#include\s*[<"]([^">]+)[">]/\1/' | sed 's/\.h$//')
		lookup_cpp "$header"
		;;

	javascript | typescript)
		# Extract module from import/require
		local module=""
		# Match: from "module" or from 'module'
		module=$(echo "$import_line" | grep -oP "from\s+['\"]\\K[^'\"]+")
		if [ -z "$module" ]; then
			# Match: require("module") or require('module')
			module=$(echo "$import_line" | grep -oP "require\\(['\"]\\K[^'\"]+")
		fi
		[ -n "$module" ] && lookup_js "$module"
		;;

	*)
		echo "Unknown language: $lang"
		;;
	esac
}

#==============================================================================
# Extract documentation content
#==============================================================================
extract_doc_content() {
	local file="$1"
	local term="$2"
	local max_lines="${3:-20}"

	if [[ $file == *.html ]]; then
		# Extract text from HTML, find section about term
		if command -v html2text &>/dev/null; then
			html2text "$file" 2>/dev/null | grep -A"$max_lines" -i "$term" | head -"$max_lines"
		elif command -v lynx &>/dev/null; then
			lynx -dump -nolist "$file" 2>/dev/null | grep -A"$max_lines" -i "$term" | head -"$max_lines"
		else
			# Basic extraction
			sed 's/<[^>]*>//g' "$file" | grep -A"$max_lines" -i "$term" | head -"$max_lines"
		fi
	elif [[ $file == *.json ]]; then
		# Pretty print JSON section
		grep -A5 "\"$term\"" "$file" 2>/dev/null
	else
		# Plain text
		grep -A"$max_lines" -i "$term" "$file" | head -"$max_lines"
	fi
}

#==============================================================================
# Main
#==============================================================================
usage() {
	cat <<EOF
Usage: $0 <term> [language] [options]

Search offline documentation for a term.

Languages: python, cpp, c_cpp, js, javascript, rust, go, shell, all

Options:
    --open      Open the documentation file (requires xdg-open)
    --extract   Extract and display relevant content
    --import    Parse and lookup an import statement
    --batch     Process multiple terms from a file

Examples:
    $0 Path python                    # Find Path in Python docs
    $0 vector cpp                     # Find vector in C++ docs
    $0 map                            # Find map in all languages
    $0 --import "from pathlib import Path" python
    $0 --batch imports.txt python
EOF
}

#!/bin/bash
# Python documentation lookup.
#
# Sourced by lookup_docs.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

#==============================================================================
# Python-specific lookup
#==============================================================================
lookup_python() {
	local term="$1"
	local in_module="$2" # Optional: look for term within this module
	local doc_dir="$DOCS_DIR/python"
	local result=""
	local desc=""

	# Normalize term (preserve case for True/False/None)
	local term_lower
	term_lower=$(echo "$term" | tr '[:upper:]' '[:lower:]')

	# If looking for a term within a specific module
	if [ -n "$in_module" ]; then
		local module_lower
		module_lower=$(echo "$in_module" | tr '[:upper:]' '[:lower:]')

		if [ -f "$doc_dir/library/${module_lower}.html" ]; then
			# Find anchor for the specific item in the module
			local anchor
			anchor=$(grep -oP "id=\"[^\"]*${term}[^\"]*\"" "$doc_dir/library/${module_lower}.html" 2>/dev/null | head -1 | sed 's/id="//;s/"//')

			if [ -n "$anchor" ]; then
				result="$doc_dir/library/${module_lower}.html#$anchor"
				desc="Python: $in_module.$term"
			else
				# Just link to the module
				result="$doc_dir/library/${module_lower}.html"
				desc="Python: $term in module $in_module"
			fi
			echo "$result|$desc"
			return 0
		fi
	fi

	local _kw
	_kw="$(python_keyword_doc "$doc_dir" "$term" "$term_lower")"
	IFS=$'\t' read -r result desc <<<"$_kw"

	# Verify file exists for keyword lookups
	if [ -n "$result" ] && [ ! -f "${result%%#*}" ]; then
		result=""
		desc=""
	fi

	#--------------------------------------------------------------------------
	# PRIORITY 2: Check if it's a module (pathlib, os, sys, etc.)
	#--------------------------------------------------------------------------
	if [ -z "$result" ] && [ -f "$doc_dir/library/${term_lower}.html" ]; then
		result="$doc_dir/library/${term_lower}.html"
		desc="Python module: $term"
	fi

	#--------------------------------------------------------------------------
	# PRIORITY 3: Built-in functions (library/functions.html)
	#--------------------------------------------------------------------------
	if [ -z "$result" ] && [ -f "$doc_dir/library/functions.html" ]; then
		if grep -q "id=\"$term_lower\"" "$doc_dir/library/functions.html" 2>/dev/null; then
			result="$doc_dir/library/functions.html#$term_lower"
			desc="Python built-in function: $term"
		fi
	fi

	#--------------------------------------------------------------------------
	# PRIORITY 4: Built-in types (library/stdtypes.html)
	#--------------------------------------------------------------------------
	if [ -z "$result" ]; then
		case "$term_lower" in
		str | string)
			result="$doc_dir/library/stdtypes.html#str"
			desc="Python: str type"
			;;
		int | integer)
			result="$doc_dir/library/stdtypes.html#int"
			desc="Python: int type"
			;;
		float)
			result="$doc_dir/library/stdtypes.html#float"
			desc="Python: float type"
			;;
		list)
			result="$doc_dir/library/stdtypes.html#list"
			desc="Python: list type"
			;;
		dict | dictionary)
			result="$doc_dir/library/stdtypes.html#dict"
			desc="Python: dict type"
			;;
		set)
			result="$doc_dir/library/stdtypes.html#set"
			desc="Python: set type"
			;;
		tuple)
			result="$doc_dir/library/stdtypes.html#tuple"
			desc="Python: tuple type"
			;;
		bool | boolean)
			result="$doc_dir/library/stdtypes.html#boolean-values"
			desc="Python: bool type"
			;;
		bytes)
			result="$doc_dir/library/stdtypes.html#bytes"
			desc="Python: bytes type"
			;;
		esac
	fi

	#--------------------------------------------------------------------------
	# PRIORITY 5: Check for class/function in module docs (exact id match)
	#--------------------------------------------------------------------------
	if [ -z "$result" ]; then
		local found_in
		# Look for exact id match first
		found_in=$(grep -l "id=\"$term\"" "$doc_dir/library/"*.html 2>/dev/null | head -1)
		if [ -n "$found_in" ]; then
			result="$found_in#$term"
			local module
			module=$(basename "$found_in" .html)
			desc="Python: $term in module $module"
		fi
	fi

	#--------------------------------------------------------------------------
	# PRIORITY 6: Search in index
	#--------------------------------------------------------------------------
	if [ -z "$result" ] && [ -f "$INDEX_DIR/python_index.txt" ]; then
		local index_match
		index_match=$(grep -i "^$term " "$INDEX_DIR/python_index.txt" 2>/dev/null | head -1)
		if [ -n "$index_match" ]; then
			result=$(echo "$index_match" | cut -d' ' -f2-)
			desc="Python: $term (from index)"
		fi
	fi

	# NO full-text search fallback - it produces garbage results
	# If we can't find a specific doc, return nothing (will fall back to online)

	if [ -n "$result" ]; then
		echo "$result|$desc"
	fi
}

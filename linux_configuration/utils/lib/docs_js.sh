#!/bin/bash
# JavaScript documentation lookup.
#
# Sourced by lookup_docs.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

#==============================================================================
# JavaScript/MDN specific lookup
# Searches the cloned MDN content repository
#==============================================================================
lookup_js() {
	local term="$1"
	local mdn_dir="$DOCS_DIR/mdn-content/files/en-us"

	# Normalize term for searching
	local term_lower
	term_lower=$(echo "$term" | tr '[:upper:]' '[:lower:]')

	# Handle common statement aliases (MDN uses if...else, try...catch, etc.)
	local statement_aliases=(
		"if:if...else"
		"else:if...else"
		"try:try...catch"
		"catch:try...catch"
		"finally:try...catch"
		"do:do...while"
		"while:while"
		"for:for"
		"switch:switch"
		"case:switch"
		"default:switch"
	)

	for alias in "${statement_aliases[@]}"; do
		local key="${alias%%:*}"
		local value="${alias##*:}"
		if [ "$term_lower" = "$key" ]; then
			local stmt_dir="$mdn_dir/web/javascript/reference/statements/$value"
			if [ -d "$stmt_dir" ] && [ -f "$stmt_dir/index.md" ]; then
				local title
				title=$(grep -m1 "^title:" "$stmt_dir/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
				echo "$stmt_dir/index.md|${title:-$term}"
				return 0
			fi
		fi
	done

	# Handle boolean/null literals
	case "$term_lower" in
	true | false)
		local bool_dir="$mdn_dir/web/javascript/reference/global_objects/boolean"
		if [ -d "$bool_dir" ] && [ -f "$bool_dir/index.md" ]; then
			echo "$bool_dir/index.md|Boolean ($term)"
			return 0
		fi
		;;
	null)
		local null_dir="$mdn_dir/web/javascript/reference/operators/null"
		if [ -d "$null_dir" ] && [ -f "$null_dir/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$null_dir/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$null_dir/index.md|${title:-null}"
			return 0
		fi
		;;
	undefined)
		local undef_dir="$mdn_dir/web/javascript/reference/global_objects/undefined"
		if [ -d "$undef_dir" ] && [ -f "$undef_dir/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$undef_dir/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$undef_dir/index.md|${title:-undefined}"
			return 0
		fi
		;;
	esac

	# Search JavaScript reference directory structure (priority order)
	local search_dirs=(
		"$mdn_dir/web/javascript/reference/statements"
		"$mdn_dir/web/javascript/reference/operators"
		"$mdn_dir/web/javascript/reference/global_objects"
		"$mdn_dir/web/javascript/reference/functions"
		"$mdn_dir/web/javascript/reference/classes"
	)

	for search_dir in "${search_dirs[@]}"; do
		if [ -d "$search_dir" ]; then
			# Look for exact directory match (MDN uses directories with index.md)
			local found_dir
			found_dir=$(find "$search_dir" -maxdepth 2 -type d -iname "$term" 2>/dev/null | head -1)
			if [ -n "$found_dir" ] && [ -f "$found_dir/index.md" ]; then
				local title
				title=$(grep -m1 "^title:" "$found_dir/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
				echo "$found_dir/index.md|${title:-$term}"
				return 0
			fi
		fi
	done

	# Search Web APIs - prioritize *_api directories for common terms
	if [ -d "$mdn_dir/web/api" ]; then
		# First try <term>_api directory (e.g., fetch_api, console_api)
		local api_dir="$mdn_dir/web/api/${term_lower}_api"
		if [ -d "$api_dir" ] && [ -f "$api_dir/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$api_dir/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$api_dir/index.md|${title:-$term API}"
			return 0
		fi

		# Then try exact top-level API interface (e.g., Console, Document, Element)
		local found
		found=$(find "$mdn_dir/web/api" -maxdepth 1 -type d -iname "$term" 2>/dev/null | head -1)
		if [ -n "$found" ] && [ -f "$found/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$found/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$found/index.md|${title:-$term}"
			return 0
		fi

		# Try window/<term> for global functions like alert, confirm, etc.
		local window_method="$mdn_dir/web/api/window/${term_lower}"
		if [ -d "$window_method" ] && [ -f "$window_method/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$window_method/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$window_method/index.md|${title:-Window.$term()}"
			return 0
		fi

		# Search nested API methods
		found=$(find "$mdn_dir/web/api" -maxdepth 3 -type d -iname "$term" 2>/dev/null | head -1)
		if [ -n "$found" ] && [ -f "$found/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$found/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$found/index.md|${title:-$term}"
			return 0
		fi
	fi

	# Now try partial matches in Global Objects (e.g., Array.from, Object.keys)
	if [ -d "$mdn_dir/web/javascript/reference/global_objects" ]; then
		local found
		found=$(find "$mdn_dir/web/javascript/reference/global_objects" -maxdepth 2 -type d -iname "*${term}*" 2>/dev/null | head -1)
		if [ -n "$found" ] && [ -f "$found/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$found/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$found/index.md|${title:-$term}"
			return 0
		fi
	fi

	# Glossary as last resort
	if [ -d "$mdn_dir/glossary" ]; then
		local found
		found=$(find "$mdn_dir/glossary" -maxdepth 1 -type d -iname "$term" 2>/dev/null | head -1)
		if [ -n "$found" ] && [ -f "$found/index.md" ]; then
			local title
			title=$(grep -m1 "^title:" "$found/index.md" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
			echo "$found/index.md|${title:-$term}"
			return 0
		fi
	fi

	return 1
}

#!/usr/bin/env bash
# lib/study_doc_lookup.sh — resolve a term to documentation.
#
# get_doc_url dispatches to the per-language builders in study_doc_urls*.sh;
# lookup_offline prefers a local mirror when one is installed, so a generated
# card can cite a file an assistant can actually read rather than a URL it
# would have to fetch. detect_language picks the primary language out of the
# tokei stats the analysis step wrote.

#==============================================================================
# Offline Documentation Lookup (preferred if available)
#==============================================================================
lookup_offline() {
	local term="$1"
	local lang="$2"
	# Optional: the full import line, for import-aware lookups. Documented as
	# optional and genuinely called without it, so it is defaulted rather than
	# required -- under `set -u` a bare "$3" aborts instead.
	local import_line="${3:-}"

	if ! $USE_OFFLINE_DOCS; then
		return 1
	fi

	local result
	if [ -n "$import_line" ]; then
		# Use import-aware lookup - get the line with the file path
		result=$("$LOOKUP_SCRIPT" --import "$import_line" "$lang" 2>/dev/null | grep "^/" | head -1)
	else
		result=$("$LOOKUP_SCRIPT" "$term" "$lang" 2>/dev/null | grep "^File:" | head -1 | sed 's/^File: //')
	fi

	if [ -n "$result" ]; then
		# Extract file path (before the | separator)
		local file_path
		file_path=$(echo "$result" | cut -d'|' -f1)
		if [ -n "$file_path" ]; then
			echo "$file_path"
			return 0
		fi
	fi

	return 1
}

#==============================================================================
# Get documentation URL for a term based on detected language
#==============================================================================
get_doc_url() {
	local term="$1"
	local lang="$2"
	# Optional, as above: 8 of the 9 call sites pass only a term and a language.
	local import_line="${3:-}"

	# Try offline docs first
	local offline_result
	offline_result=$(lookup_offline "$term" "$lang" "$import_line")
	if [ -n "$offline_result" ]; then
		echo "$offline_result"
		return 0
	fi

	# For TypeScript, also try JavaScript offline docs (most TS keywords are JS)
	if [[ $lang == "typescript" || $lang == "ts" || $lang == "tsx" ]]; then
		offline_result=$(lookup_offline "$term" "js" "$import_line")
		if [ -n "$offline_result" ]; then
			echo "$offline_result"
			return 0
		fi
	fi

	# Fall back to online URLs
	case "$lang" in
	python | py)
		python_doc_url "$term"
		;;
	javascript | js | jsx)
		js_doc_url "$term"
		;;
	typescript | ts | tsx)
		# For TypeScript, try JS doc first (since most keywords are shared)
		# Only use TS-specific docs for TS-only features
		case "$term" in
		interface | type | enum | namespace | declare | readonly | abstract | implements | keyof | infer | as | is | asserts | satisfies | override | Partial | Required | Readonly | Record | Pick | Omit | Exclude | Extract | NonNullable | ReturnType | Parameters | InstanceType | Awaited)
			ts_doc_url "$term"
			;;
		*)
			js_doc_url "$term"
			;;
		esac
		;;
	c)
		c_doc_url "$term"
		;;
	cpp | c++ | cc | cxx)
		cpp_doc_url "$term"
		;;
	rust | rs)
		rust_doc_url "$term"
		;;
	go)
		go_doc_url "$term"
		;;
	ruby | rb)
		ruby_doc_url "$term"
		;;
	java)
		java_doc_url "$term"
		;;
	shell | bash | sh)
		shell_doc_url "$term"
		;;
	*)
		echo "https://devdocs.io/#q=$term"
		;;
	esac
}

#==============================================================================
# Detect primary language from results
#==============================================================================
detect_language() {
	if [ -f "$RESULTS_DIR/tokei_stats.txt" ]; then
		# Parse tokei output to find most used language
		grep -E "^\s+(Python|JavaScript|TypeScript|C\+\+|C |Rust|Go|Ruby|Java|Shell)" "$RESULTS_DIR/tokei_stats.txt" 2>/dev/null |
			head -1 |
			awk '{print tolower($1)}' |
			sed 's/c++/cpp/'
	else
		echo "unknown"
	fi
}

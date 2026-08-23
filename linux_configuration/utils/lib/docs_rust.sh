#!/bin/bash
# Rust documentation lookup.
#
# Sourced by lookup_docs.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

#==============================================================================
# Rust specific lookup
#==============================================================================
lookup_rust() {
	local term="$1"
	local result=""
	local desc=""

	if command -v rustup &>/dev/null; then
		# Use rustup doc to get path
		local rust_doc_path
		rust_doc_path=$(rustup doc --path 2>/dev/null | head -1 | xargs dirname 2>/dev/null)

		# Search in std docs
		if [ -d "$rust_doc_path/std" ]; then
			local found
			found=$(find "$rust_doc_path/std" -name "*${term}*" -type f 2>/dev/null | head -1)
			if [ -n "$found" ]; then
				result="$found"
				desc="Rust: $term"
			fi
		fi
	fi

	if [ -n "$result" ]; then
		echo "$result|$desc"
	fi
}

#==============================================================================
# Go specific lookup
#==============================================================================
lookup_go() {
	local term="$1"
	local result=""
	local desc=""

	if command -v go &>/dev/null; then
		# Check if it's a stdlib package
		if go doc "$term" &>/dev/null; then
			result="go doc $term"
			desc="Go package: $term (use 'go doc $term' to view)"
		fi
	fi

	if [ -n "$result" ]; then
		echo "$result|$desc"
	fi
}

#==============================================================================
# Shell specific lookup
#==============================================================================
lookup_shell() {
	local term="$1"
	local doc_dir="$DOCS_DIR/shell"
	local result=""
	local desc=""

	# Check bash builtins
	if [ -f "$doc_dir/bash_builtins.txt" ]; then
		if grep -q "=== $term ===" "$doc_dir/bash_builtins.txt" 2>/dev/null; then
			result="$doc_dir/bash_builtins.txt"
			desc="Bash builtin: $term"
		fi
	fi

	# Check common commands
	if [ -z "$result" ] && [ -f "$doc_dir/common_commands.txt" ]; then
		if grep -q "^$term" "$doc_dir/common_commands.txt" 2>/dev/null; then
			local cmd_desc
			cmd_desc=$(grep "^$term" "$doc_dir/common_commands.txt" | head -1)
			result="$doc_dir/common_commands.txt"
			desc="Shell command: $cmd_desc"
		fi
	fi

	# Try man page
	if [ -z "$result" ]; then
		local man_path
		man_path=$(man -w "$term" 2>/dev/null)
		if [ -n "$man_path" ]; then
			result="man $term"
			desc="Manual page: $term (use 'man $term' to view)"
		fi
	fi

	if [ -n "$result" ]; then
		echo "$result|$desc"
	fi
}

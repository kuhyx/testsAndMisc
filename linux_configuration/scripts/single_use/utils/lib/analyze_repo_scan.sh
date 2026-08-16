#!/bin/bash
# Output formatting, gitignore-aware file discovery, fast word counting and
# language detection.
#
# Sourced by analyze_repo.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and reads
# RESPECT_GITIGNORE, EXCLUDE_DIRS, SCRIPT_DIR and the colour constants that the
# entry script sets above the source line.

print_header() {
	echo ""
	echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
	echo -e "${GREEN}  $1${NC}"
	echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
	echo ""
}

print_subheader() {
	echo ""
	echo -e "${YELLOW}--- $1 ---${NC}"
	echo ""
}

# Check if we're in a git repository
is_git_repo() {
	git rev-parse --is-inside-work-tree &>/dev/null
}

# Helper function to find files while respecting exclusions
# Usage: find_files "*.c" or find_files "*.py" "*.pyx"
find_files() {
	local patterns=("$@")

	if [ "$RESPECT_GITIGNORE" = true ]; then
		if is_git_repo; then
			# Use git ls-files which respects .gitignore automatically
			# This includes tracked files and untracked files not in .gitignore
			local git_patterns=()
			for pat in "${patterns[@]}"; do
				git_patterns+=("$pat")
			done
			# Get tracked files + untracked (but not ignored) files
			{
				git ls-files -- "${git_patterns[@]}" 2>/dev/null
				git ls-files --others --exclude-standard -- "${git_patterns[@]}" 2>/dev/null
			} | sort -u
		else
			# Not a git repo - fall back to manual exclusion
			local find_args=()
			for i in "${!patterns[@]}"; do
				if [ "$i" -eq 0 ]; then
					find_args+=(-name "${patterns[$i]}")
				else
					find_args+=(-o -name "${patterns[$i]}")
				fi
			done
			find . -type f \( "${find_args[@]}" \) 2>/dev/null | grep -Ev "/($EXCLUDE_DIRS)/"
		fi
	else
		# No filtering - find all files
		local find_args=()
		for i in "${!patterns[@]}"; do
			if [ "$i" -eq 0 ]; then
				find_args+=(-name "${patterns[$i]}")
			else
				find_args+=(-o -name "${patterns[$i]}")
			fi
		done
		find . -type f \( "${find_args[@]}" \) 2>/dev/null
	fi
}

# Count files matching pattern (respecting exclusions)
count_files() {
	find_files "$@" | wc -l
}

# Fast word counting: 'counts' (Rust) if available, else the Python fallback.
fast_count() {
	local top_n="${1:-50}"
	if command -v counts &>/dev/null; then
		counts 2>/dev/null | head -n "$((top_n + 1))" | tail -n "$top_n"
	else
		python3 "$SCRIPT_DIR/fast_count.py" "$top_n"
	fi
}

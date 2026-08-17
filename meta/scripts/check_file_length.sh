#!/usr/bin/env bash

# ============================================================================
# Enforce the repo-wide source-file length cap.
#
# Every source file must be at most MAX_LINES lines. The cap exists so that a
# file stays readable in one sitting and so that a split is forced while the
# seams are still obvious, rather than after a file has grown past rescue.
#
# Checks tracked source files only. Data, docs, config and vendored trees are
# out of scope: a 900-line lockfile or an HTML report is not something a
# human is expected to read top to bottom, so a cap there is noise.
#
#   check_file_length.sh --all            # every tracked source file
#   check_file_length.sh <file>...        # only the named files
#
# Exits 0 when everything is within the cap, 1 when anything is over.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly MAX_LINES=250

# Extensions that carry hand-written logic. Kept explicit rather than
# inverted: a new data format should not silently become subject to the cap.
readonly SOURCE_EXTENSIONS=(
	sh bash zsh
	py
	kt kts
	dart
	ts tsx js jsx
)

# Vendored or generated trees. Their length is upstream's business, and a
# split would be reverted by the next sync.
readonly EXCLUDED_PREFIXES=(
	third_party/
	docs/superpowers/
)

usage() {
	echo "Usage: $SCRIPT_NAME [--all | <file>...]"
	echo "Options:"
	echo "  --all         Check every tracked source file"
	echo "  -h, --help    Show this help"
	echo
	echo "Source files must be at most $MAX_LINES lines."
	exit 0
}

# True when the path carries a source extension we cap.
is_source_file() {
	local path="$1" ext="${1##*.}"
	# A path with no dot in its final component has no extension to match.
	[[ "$path" == *.* ]] || return 1
	local candidate
	for candidate in "${SOURCE_EXTENSIONS[@]}"; do
		[[ "$ext" == "$candidate" ]] && return 0
	done
	return 1
}

# True when the path sits under a tree we deliberately do not police.
is_excluded() {
	local path="$1" prefix
	for prefix in "${EXCLUDED_PREFIXES[@]}"; do
		[[ "$path" == "$prefix"* ]] && return 0
	done
	return 1
}

# Print "<lines>\t<path>" for each in-scope file that exceeds the cap.
report_violations() {
	local path lines
	for path in "$@"; do
		[[ -f "$path" ]] || continue
		is_source_file "$path" || continue
		is_excluded "$path" && continue
		lines=$(wc -l <"$path")
		if ((lines > MAX_LINES)); then
			printf '%s\t%s\n' "$lines" "$path"
		fi
	done
}

collect_all_tracked() {
	git ls-files
}

main() {
	local -a targets=()

	if [[ $# -eq 0 ]]; then
		echo "Error: pass --all or one or more file paths" >&2
		exit 1
	fi

	if [[ "$1" == "--all" ]]; then
		mapfile -t targets < <(collect_all_tracked)
	else
		targets=("$@")
	fi

	local violations
	violations="$(report_violations "${targets[@]}" | sort -rn)"

	if [[ -z "$violations" ]]; then
		echo "check_file_length: all checked files are within $MAX_LINES lines"
		return 0
	fi

	local count
	count="$(printf '%s\n' "$violations" | wc -l)"

	echo "check_file_length: $count file(s) over the $MAX_LINES-line cap:" >&2
	printf '%s\n' "$violations" | while IFS=$'\t' read -r lines path; do
		printf '  %5d  %s (+%d)\n' "$lines" "$path" "$((lines - MAX_LINES))" >&2
	done
	return 1
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	-h | --help)
		usage
		;;
	*)
		break
		;;
	esac
done

main "$@"

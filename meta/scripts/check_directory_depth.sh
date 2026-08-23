#!/usr/bin/env bash

# ============================================================================
# Enforce the repo-wide directory-depth cap.
#
# A tracked file may sit at most MAX_DEPTH directories below the repo root.
# The cap exists so that this repo stays a home for small, findable scripts:
# once a subtree needs its own taxonomy several levels deep, it has outgrown
# "misc" and belongs in its own repository.
#
# Exempt, by path prefix:
#   third_party/       vendored - its shape is upstream's business
#   docs/superpowers/  hook-generated bookkeeping, not hand-placed
#   .github/skills/    layout fixed by the agent harness
#   C/                 a C project: its own build layout, not taxonomy
#   artgate/           a Flask app; routes/ and styles/ are framework shape
#   misc/tools/        one tool split across modules to satisfy the line cap
#   docs/              prose trees; chapter folders are not code taxonomy
#   dwm/               an upstream-shaped suckless tree
#   utils/data/        data files beside the script that reads them
#   zsh/scratchpad/    a single scratch file
#   run_all/           the aggregate runner's own fixtures
#
# Exempt, by path segment: `lib/` and `tests/` are structural, not taxonomic
# - a library split out to satisfy the 250-line cap, and the test suite the
# shell-coverage ratchet requires beside it. Capping them would force one
# gate to fight another. The same argument covers the directories whose name
# is dictated by an external format rather than chosen by us: systemd unit
# dirs, pacman/git hook dirs, GitHub workflow dirs, patch sets and test
# fixtures. Each is matched as a whole segment, so `libvirt/` or `binutils/`
# is unaffected.
#
#   check_directory_depth.sh --all         # every tracked file
#   check_directory_depth.sh <file>...     # only the named files
#   check_directory_depth.sh --all --warn  # report but always exit 0
#
# Exits 0 when everything is within the cap, 1 when anything is over.
# With --warn it reports violations and still exits 0; the hook runs in that
# mode because 47 paths under `periodic_background/{hosts,digital_wellbeing}`
# are over the cap and can only be fixed by extracting those two units, which
# is blocked on a manual guard repoint. Drop --warn from the hook once they
# are out; the cap is then enforced for real.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly MAX_DEPTH=2

readonly EXCLUDED_PREFIXES=(
	third_party/
	docs/superpowers/
	.github/skills/
	# Whole projects that carry their own conventional layout.
	linux_configuration/C/
	linux_configuration/dwm/
	python_pkg/artgate/
	# A single tool split into modules to satisfy the 250-line cap.
	linux_configuration/misc/tools/
	# Prose trees: a chapter folder is not code taxonomy.
	linux_configuration/docs/
	# One-off leaves, listed explicitly rather than exempting the segment
	# name everywhere: `data` and `scratchpad` are too generic for that.
	linux_configuration/utils/data/
	linux_configuration/zsh/scratchpad/
	meta/scripts/run_all/
)

# Directory names that never count as taxonomy. Matched as whole path
# segments, so a file called `lib.sh` or a directory `libvirt/` is unaffected.
readonly EXEMPT_SEGMENTS=(
	lib
	tests
	# Names dictated by an external format, not chosen as a category.
	systemd
	hooks
	workflows
	patches
	fixtures
)

WARN_ONLY=0

usage() {
	echo "Usage: $SCRIPT_NAME [--warn] [--all | <file>...]"
	echo "Options:"
	echo "  --all         Check every tracked file"
	echo "  --warn        Report violations but always exit 0"
	echo "  -h, --help    Show this help"
	echo
	echo "Files must sit at most $MAX_DEPTH directories below the repo root."
	exit 0
}

# True when the path sits under a tree we deliberately do not police.
is_excluded() {
	local path="$1" prefix
	for prefix in "${EXCLUDED_PREFIXES[@]}"; do
		[[ "$path" == "$prefix"* ]] && return 0
	done
	return 1
}

# True when any DIRECTORY component of the path is an exempt segment. The
# final component is the filename and is deliberately not considered.
has_exempt_segment() {
	local path="$1" dir="${1%/*}"
	# No slash means the file is at the root: no directory components at all.
	[[ "$path" == */* ]] || return 1
	local IFS=/
	local -a parts
	read -r -a parts <<<"$dir"
	local part segment
	for part in "${parts[@]}"; do
		for segment in "${EXEMPT_SEGMENTS[@]}"; do
			[[ "$part" == "$segment" ]] && return 0
		done
	done
	return 1
}

# Number of directories above the file: a/b/c.sh -> 2.
depth_of() {
	local path="$1"
	[[ "$path" == */* ]] || {
		echo 0
		return
	}
	local dir="${path%/*}"
	echo $(($(tr -cd '/' <<<"$dir" | wc -c) + 1))
}

# Print "<depth>\t<path>" for each in-scope file that exceeds the cap.
report_violations() {
	local path depth
	for path in "$@"; do
		[[ -n "$path" ]] || continue
		is_excluded "$path" && continue
		has_exempt_segment "$path" && continue
		depth="$(depth_of "$path")"
		if ((depth > MAX_DEPTH)); then
			printf '%s\t%s\n' "$depth" "$path"
		fi
	done
}

main() {
	local -a targets=()

	if [[ $# -eq 0 ]]; then
		echo "Error: pass --all or one or more file paths" >&2
		exit 1
	fi

	if [[ "$1" == "--all" ]]; then
		if [[ $# -gt 1 ]]; then
			echo "Error: --all takes no further arguments (got: ${*:2})" >&2
			echo "Note: options must precede --all, e.g. --warn --all" >&2
			exit 1
		fi
		mapfile -t targets < <(git ls-files)
	else
		targets=("$@")
	fi

	local violations
	violations="$(report_violations "${targets[@]}" | sort -rn)"

	if [[ -z "$violations" ]]; then
		echo "check_directory_depth: all checked paths are within $MAX_DEPTH directories"
		return 0
	fi

	local count
	count="$(printf '%s\n' "$violations" | wc -l)"

	echo "check_directory_depth: $count path(s) over the $MAX_DEPTH-directory cap:" >&2
	printf '%s\n' "$violations" | while IFS=$'\t' read -r depth path; do
		printf '  %3d  %s (+%d)\n' "$depth" "$path" "$((depth - MAX_DEPTH))" >&2
	done

	if ((WARN_ONLY)); then
		echo "check_directory_depth: --warn given, not failing" >&2
		return 0
	fi
	return 1
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	-h | --help)
		usage
		;;
	--warn)
		WARN_ONLY=1
		shift
		;;
	*)
		break
		;;
	esac
done

main "$@"

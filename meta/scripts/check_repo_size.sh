#!/usr/bin/env bash

# ============================================================================
# Enforce a ceiling on the number of source files in the repo.
#
# The companion to the directory-depth cap. Depth stops any one subtree from
# growing its own taxonomy; this stops the repo as a whole from quietly
# becoming the place everything lands. When the count reaches the ceiling the
# answer is to extract a unit into its own repository - not to raise the
# number because the commit is inconvenient.
#
# "Source" means tracked files that a human wrote and maintains here. Three
# categories are therefore excluded from the count:
#
#   third_party/        vendored; upstream decides how many files it has
#   docs/superpowers/   hook-generated evidence/contract bookkeeping, which
#                       grows once per commit and would dominate the number
#   .hippo/             agent-generated store, same argument
#
# Counting is done with `git ls-files`, never `find`: the working tree also
# holds untracked extraction leftovers running to tens of thousands of files,
# and a `find`-based count would be meaningless.
#
# The count is always printed, so the threshold can be audited from any CI log
# rather than being taken on trust.
#
#   check_repo_size.sh            # count and enforce
#   check_repo_size.sh --count    # print the number only, always exit 0
#
# Exits 0 when at or under the ceiling, 1 when over.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

# Set from the 1049 files counted when this gate was written, plus room to
# work. Extract a unit rather than raising it; see the header.
readonly MAX_SOURCE_FILES=1200

readonly EXCLUDED_PREFIXES=(
	third_party/
	docs/superpowers/
	.hippo/
)

COUNT_ONLY=0

usage() {
	echo "Usage: $SCRIPT_NAME [--count]"
	echo "Options:"
	echo "  --count       Print the source-file count and exit 0"
	echo "  -h, --help    Show this help"
	echo
	echo "Fails when tracked source files exceed $MAX_SOURCE_FILES."
	exit 0
}

# Tracked files minus the generated and vendored trees. Printed one per line.
source_files() {
	local -a filter=()
	local prefix
	for prefix in "${EXCLUDED_PREFIXES[@]}"; do
		filter+=(-e "^${prefix}")
	done
	# grep exits 1 when it filters everything out; that is not an error here.
	git ls-files | grep -v "${filter[@]}" || true
}

main() {
	local count
	count="$(source_files | wc -l)"

	if ((COUNT_ONLY)); then
		echo "$count"
		return 0
	fi

	if ((count > MAX_SOURCE_FILES)); then
		echo "check_repo_size: $count source files, over the $MAX_SOURCE_FILES ceiling" >&2
		echo "Extract a unit into its own repo rather than raising the cap." >&2
		return 1
	fi

	echo "check_repo_size: $count source files (ceiling $MAX_SOURCE_FILES)"
	return 0
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	-h | --help)
		usage
		;;
	--count)
		COUNT_ONLY=1
		shift
		;;
	*)
		echo "Unknown option: $1" >&2
		exit 1
		;;
	esac
done

main

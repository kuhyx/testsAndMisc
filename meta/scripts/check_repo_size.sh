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
# The generated trees are excluded from that count but capped separately: they
# grow about one file per commit, which is what made a 655-file prune
# necessary in the first place. Capping them here means the next overflow
# fails a commit instead of being noticed months later.
#
#   check_repo_size.sh            # count and enforce
#   check_repo_size.sh --count    # print the number only, always exit 0
#
# Exits 0 when at or under every ceiling, 1 when over any of them.
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

# Per-commit bookkeeping. Pruned to 20 each (plus a template) on 2026-08-23;
# the cap is the headroom that prune bought, so the tree cannot silently
# return to the 695 files it held before. When this fails, prune - do not
# raise it.
readonly ARTIFACT_DIRS=(
	docs/superpowers/evidence
	docs/superpowers/contracts
)
readonly MAX_ARTIFACTS_PER_DIR=60

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

# Fail when a bookkeeping directory has grown past its cap. Reports every
# offending directory rather than stopping at the first.
check_artifact_dirs() {
	local dir n over=0
	for dir in "${ARTIFACT_DIRS[@]}"; do
		n="$(git ls-files "$dir" | wc -l)"
		if ((n > MAX_ARTIFACTS_PER_DIR)); then
			echo "check_repo_size: $dir holds $n files, over the $MAX_ARTIFACTS_PER_DIR cap" >&2
			over=1
		fi
	done
	((over)) && {
		echo "Prune the oldest artifacts; they stay available in git history." >&2
		return 1
	}
	return 0
}

main() {
	local count
	count="$(source_files | wc -l)"

	if ((COUNT_ONLY)); then
		echo "$count"
		return 0
	fi

	local failed=0

	if ((count > MAX_SOURCE_FILES)); then
		echo "check_repo_size: $count source files, over the $MAX_SOURCE_FILES ceiling" >&2
		echo "Extract a unit into its own repo rather than raising the cap." >&2
		failed=1
	fi

	check_artifact_dirs || failed=1

	((failed)) && return 1

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

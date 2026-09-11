#!/bin/bash

# ============================================================================
# prettier --check, memory-capped and result-cached.
#
# Two problems this solves:
#
# 1. Memory. Prettier runs inside its own systemd-run scope so its budget is
#    independent of the outer pre-push cgroup, which has already accumulated
#    page cache from pytest/mypy/pylint.
#
# 2. Latency. Prettier is a pre-push hook precisely because Node's startup
#    dominates its runtime, and pre-commit chunks a large file list into
#    several invocations -- a 104-file push paid three cold Node starts and
#    ~13s wall clock. A file whose content, prettier version and prettier
#    config are all unchanged since the last clean check cannot have become
#    unformatted, so its verdict is cached and it never reaches Node. The
#    common push touches files that are already clean, which makes the whole
#    hook a handful of hashes and no Node process at all.
#
# The cache is keyed on content, so it cannot go stale: edit a file, bump
# prettier, or change .prettierrc and the key changes with it.
# ============================================================================

set -euo pipefail

CACHE_ROOT="${PRETTIER_GATE_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/prettier-gate}"
readonly CACHE_ROOT
# Enough entries for several branches' worth of files; pruned wholesale rather
# than per-entry, because an empty cache costs one slow run, not correctness.
readonly MAX_ENTRIES=20000

# Everything that can change prettier's verdict without changing the file.
config_fingerprint() {
	local version config
	version="$(prettier --version 2>/dev/null || echo unknown)"
	config="$(
		cat .prettierrc .prettierrc.* .prettierignore prettier.config.* 2>/dev/null
		true
	)"
	printf '%s\n%s' "$version" "$config" | sha256sum | cut -d' ' -f1
}

# One sha256sum call for the whole list: per-file forks cost more than the
# hashing does.
cache_keys() {
	local fingerprint="$1"
	shift
	sha256sum -- "$@" 2>/dev/null | while read -r digest _; do
		printf '%s-%s\n' "$fingerprint" "$digest"
	done
}

prune_if_huge() {
	local count
	count="$(find "$CACHE_ROOT" -maxdepth 1 -type f 2>/dev/null | wc -l)"
	if ((count > MAX_ENTRIES)); then
		rm -rf "${CACHE_ROOT:?}"
		mkdir -p "$CACHE_ROOT"
	fi
}

run_prettier() {
	export NODE_OPTIONS="${NODE_OPTIONS:-} --max-old-space-size=384"
	if command -v systemd-run >/dev/null 2>&1; then
		systemd-run --user --scope --quiet --collect \
			-p MemoryMax=512M \
			-p MemorySwapMax=0 \
			-- prettier --check "$@"
		return
	fi
	prettier --check "$@"
}

main() {
	if [ $# -eq 0 ]; then
		exit 0
	fi

	mkdir -p "$CACHE_ROOT"
	prune_if_huge

	local fingerprint
	fingerprint="$(config_fingerprint)"

	# Pair each file with its key, then split into "already known clean" and
	# "must be checked". readarray keeps this to two subshells regardless of
	# how many files pre-commit passed.
	local -a keys=() todo=() todo_keys=()
	readarray -t keys < <(cache_keys "$fingerprint" "$@")
	if ((${#keys[@]} != $#)); then
		# A file vanished between pre-commit's listing and now: fall back to
		# checking everything rather than mis-pairing files with digests.
		run_prettier "$@"
		exit $?
	fi

	local i=0 file
	for file in "$@"; do
		if [[ ! -f "$CACHE_ROOT/${keys[i]}" ]]; then
			todo+=("$file")
			todo_keys+=("${keys[i]}")
		fi
		i=$((i + 1))
	done

	if ((${#todo[@]} == 0)); then
		printf 'prettier: %d file(s) unchanged since their last clean check\n' "$#"
		exit 0
	fi

	run_prettier "${todo[@]}"

	# Only a clean verdict is recorded; a failure must be re-checked next time.
	local key
	for key in "${todo_keys[@]}"; do
		: >"$CACHE_ROOT/$key"
	done
}

main "$@"

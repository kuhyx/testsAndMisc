#!/usr/bin/env bash
# shellcheck shell=bash

# ============================================================================
# Memory probe for ci_mirror.sh.
#
# The gate runs `pre-commit run --all-files` and the pytest suite at the same
# time. Measured peaks: the pre-commit tree reaches ~1.75 GiB (mypy and pylint
# over the whole repo) and the pytest scope ~0.29 GiB, so the pair needs
# ~2 GiB simultaneously. The pytest scope runs under MemoryMax=2G with
# MemorySwapMax=0, which means that on a machine already under pressure it is
# the one the kernel kills - surfacing as "1798 passed" immediately followed
# by "Killed" and a failed push that has nothing to do with the code.
#
# Sourced by ci_mirror.sh; not meant to be executed directly.
# ============================================================================

# Below this much available memory the two heavy gates run one after the
# other instead of concurrently. 4 GiB is the ~2 GiB they need at the same
# instant plus the same again of headroom, because MemAvailable does not
# account for what they are about to allocate.
readonly SERIAL_BELOW_MIB=4096

# MemAvailable in MiB, read straight from /proc rather than parsing `free`.
# Returns a large number when /proc is unreadable so the fast path is kept:
# this is an optimisation guard, not a correctness gate.
available_mem_mib() {
	local key value kib=""
	while read -r key value _; do
		if [[ "$key" == "MemAvailable:" ]]; then
			kib="$value"
			break
		fi
	done </proc/meminfo
	if [[ -z "$kib" ]]; then
		echo 999999
		return
	fi
	echo $((kib / 1024))
}

# True when the machine is too tight to run the two heavy gates at once.
# Exposed as a predicate rather than a bare threshold so the constant has a
# use inside this file and the caller reads as intent, not arithmetic.
should_serialise_gates() {
	(($(available_mem_mib) < SERIAL_BELOW_MIB))
}

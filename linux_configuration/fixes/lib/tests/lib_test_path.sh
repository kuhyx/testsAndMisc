#!/usr/bin/env bash
# lib/tests/lib_test_path.sh — _t_hide and the shim farm it builds.
#
# Split out of lib_test_core.sh on 2026-08-23 to hold both files under the
# repo's 250-line cap. Sourced by lib_test_core.sh, not directly by tests.
set -uo pipefail

# _t_hide TOOL... — make TOOL genuinely unfindable, so has_cmd/command -v
# report it absent.
#
# A prepended stub dir cannot do this: every tool these libs probe for
# (usbreset, pactl, wpctl) really exists on an Arch desktop, so PATH has to
# stop resolving it. Dropping PATH to $FAKE_BIN alone is NOT the answer
# either -- that also hides grep, head, awk and sort, which these libs use
# on the very branch under test, turning a "not installed" case into a
# cascade of "command not found".
#
# Instead a shim dir is built containing a symlink to every real executable
# on PATH EXCEPT the hidden ones, and PATH is pointed at it.
_t_hide() {
	# Keyed by the tool list and reused, and deliberately cached OUTSIDE
	# $TEST_TMPDIR so the farm survives across test files: each file gets a
	# fresh tmpdir, so a per-file cache rebuilt the farm ~16 times per run.
	# The farm holds a symlink per executable on PATH (~13.5k on this host)
	# and costs ~4.6s to build, which was the single largest cost in the
	# suite. Its contents are a pure function of the tool list and
	# $LIB_TEST_ORIG_PATH, so sharing it changes no behaviour.
	#
	# $LIB_TEST_HIDE_CACHE is set by run_all.sh for a whole-suite run and
	# falls back to the per-file tmpdir when a test file is run on its own.
	local key="${*}"
	local hide_dir="${LIB_TEST_HIDE_CACHE:-${TEST_TMPDIR}/hidden_path}/${key// /_}"
	if [[ -d "$hide_dir" ]]; then
		PATH="${FAKE_BIN}:${hide_dir}"
		hash -r
		return 0
	fi
	# Build the FULL farm once, then copy it per tool set and delete just the
	# hidden names. Walking PATH and creating ~13.5k symlinks is the whole
	# cost; `cp -al` hard-links the symlinks instead of recreating them, which
	# turns each additional tool set from seconds into milliseconds.
	local full="${LIB_TEST_HIDE_CACHE:-${TEST_TMPDIR}/hidden_path}/__all"
	if [[ ! -d "$full" ]]; then
		mkdir -p "$full"
		local dir entry name
		local IFS=':'
		for dir in ${LIB_TEST_ORIG_PATH}; do
			[[ -d "$dir" ]] || continue
			for entry in "$dir"/*; do
				name="${entry##*/}"
				[[ -x "$entry" && ! -d "$entry" ]] || continue
				[[ -e "${full}/${name}" ]] && continue
				ln -s "$entry" "${full}/${name}" 2>/dev/null || true
			done
		done
	fi

	cp -al "$full" "$hide_dir"
	local tool
	for tool in "$@"; do
		rm -f "${hide_dir}/${tool}"
	done

	PATH="${FAKE_BIN}:${hide_dir}"
	hash -r
}

# shellcheck shell=bash
# lib/tests/coverage_tool_harness.sh — fixture for the shell-coverage tooling.
#
# Sourced, not executed. These three libs are pure file-writers and one
# predicate: given $JAIL (a temp dir) they emit run_cases.sh, cases and
# mounts.sh, and is_covered answers from the filesystem alone. Nothing here
# mounts anything, runs kcov, or needs a namespace -- the jail itself is
# exercised end-to-end by the suites that already run under it.
set -uo pipefail

PASS=0
FAIL=0

_t_pass() {
	PASS=$((PASS + 1))
	printf '  OK: %s\n' "$1"
}

_t_fail() {
	FAIL=$((FAIL + 1))
	printf '  FAIL: %s\n' "$1"
}

_t_eq() {
	if [[ "$2" == "$1" ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (want '$1', got '$2')"
	fi
}

_t_has() {
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (want a substring '$2')"
	fi
}

_t_lacks() {
	if [[ "$1" != *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (did not want substring '$2')"
	fi
}

# A throwaway $JAIL for one test file, removed on exit. The libs write into it
# unconditionally, so every case needs its own clean directory.
_t_new_jail() {
	JAIL="$(mktemp -d -t covtool-XXXXXX)"
	export JAIL
	mkdir -p "$JAIL/trace"
}

_t_drop_jail() {
	if [[ -n "${JAIL:-}" && "$JAIL" == /tmp/covtool-* ]]; then
		rm -rf "$JAIL"
	fi
}

# The literal dollar sign, built rather than written. Several assertions here
# check that a file contains an UNEXPANDED ${BASH_SOURCE} or $1, and writing
# that as a single-quoted literal trips SC2016 on every line. Composing the
# needle keeps the intent obvious and the file suppression-free.
DOLLAR='$'
export DOLLAR
readonly DOLLAR

_t_summary() {
	printf '\n%s: %d passed, %d failed\n' "$(basename "$0")" "$PASS" "$FAIL"
	[[ $FAIL -eq 0 ]]
}

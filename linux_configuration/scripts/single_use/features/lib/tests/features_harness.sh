#!/usr/bin/env bash
# lib/tests/features_harness.sh — shared fixture for the features/lib suites.
#
# Sourced, not executed. One harness per DIRECTORY, not per file: jscpd fails
# the commit above 2% duplication, and near-identical per-file harnesses are
# exactly how that trips.
#
# Unlike the digital_wellbeing harness, this one does NOT avoid the effecting
# code. Its subjects sudo-write systemd units and add nftables rules, and
# those paths are the point. They are made safe by running under
# meta/scripts/shell_coverage_jail.sh, which puts the whole suite inside a
# user+mount namespace where the write targets are bind-mounted to a
# throwaway dir. Nothing here may assume it can reach the real /etc.
set -euo pipefail

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
	if [[ $2 == "$1" ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (want '${1}', got '${2}')"
	fi
}

_t_has() {
	if [[ $1 == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (want a substring '${2}')"
	fi
}

_t_file_has() {
	if [[ -f $1 ]] && grep -q "$2" "$1"; then
		_t_pass "$3"
	else
		_t_fail "$3 (file '${1}' missing or lacks '${2}')"
	fi
}

# A function that calls `exit` would kill the test script if invoked directly
# in an `if` condition, so failures are asserted inside a subshell.
_t_exits_nonzero() {
	if ("$1" >/dev/null 2>&1); then
		_t_fail "$2 (expected a non-zero exit, got 0)"
	else
		_t_pass "$2"
	fi
}

FEATURES_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FEATURES_LIB_DIR

# The libs are sourced by their entry scripts and inherit these from above the
# source line. A missing one aborts the subject under `set -u` with no useful
# stderr, so the fixture asserts its own globals are populated rather than
# letting a typo become a silently skipped assertion.
log() { printf '[test] %s\n' "$1"; }

_t_setup_env() {
	TEST_TMPDIR="$(mktemp -d)"
	export TEST_TMPDIR
	PATH="$TEST_TMPDIR/bin:$PATH"
	export PATH
	mkdir -p "$TEST_TMPDIR/bin"
}

# Record-and-succeed stubs for commands with no useful behaviour under test.
# `sudo` is deliberately NOT stubbed: inside the jail we are already uid 0, so
# stubbing it would hide the very writes these tests exist to exercise.
_t_stub() {
	printf '#!/usr/bin/env bash\nprintf "%%s %%s\\n" "%s" "$*" >>"%s/calls.log"\nexit 0\n' \
		"$1" "$TEST_TMPDIR" >"$TEST_TMPDIR/bin/$1"
	chmod +x "$TEST_TMPDIR/bin/$1"
}

# Remove a stub AND forget it. bash caches executable locations in a hash
# table, so `command -v foo` keeps succeeding after foo is deleted until the
# table is cleared -- silently turning every "tool is missing" test into a
# "tool is present" test that asserts the opposite of its own name. Measured:
# without the `hash -r` the removed stub is STILL FOUND.
_t_unstub() {
	rm -f "$TEST_TMPDIR/bin/$1"
	hash -r
}

_t_called() {
	if [[ -f "$TEST_TMPDIR/calls.log" ]] && grep -q "$1" "$TEST_TMPDIR/calls.log"; then
		_t_pass "$2"
	else
		_t_fail "$2 (no '${1}' in the call log)"
	fi
}

_t_teardown() {
	if [[ -n ${TEST_TMPDIR:-} && -d ${TEST_TMPDIR} ]]; then
		rm -rf "$TEST_TMPDIR"
	fi
}

_t_report() {
	printf '\n%s: %d passed, %d failed\n' "${1:-tests}" "$PASS" "$FAIL"
	[[ $FAIL -eq 0 ]]
}

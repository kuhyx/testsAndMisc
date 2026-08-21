#!/usr/bin/env bash
# lib/tests/services_assert.sh — the assertion vocabulary shared by every
# check_and_enable_services test.
#
# Sourced by services_harness.sh, not directly by the tests. Split out of the
# harness purely to keep both files under the repo-wide 250-line cap, which
# applies to test files too.
#
# _t_called / _t_not_called read $DEV/calls, the log every PATH shim appends
# to, so they are only meaningful after the harness has defined $DEV.

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
	local want="$1"
	local got="$2"
	local what="$3"
	if [[ "$got" == "$want" ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (want '${want}', got '${got}')"
	fi
}

# Assert $DEV/calls contains a line matching a regex.
_t_called() {
	local pattern="$1"
	local what="$2"
	if grep -qE "$pattern" "${DEV}/calls" 2>/dev/null; then
		_t_pass "$what"
	else
		_t_fail "$what (no call matching /${pattern}/)"
	fi
}

_t_not_called() {
	local pattern="$1"
	local what="$2"
	if grep -qE "$pattern" "${DEV}/calls" 2>/dev/null; then
		_t_fail "$what (unexpected call matching /${pattern}/)"
	else
		_t_pass "$what"
	fi
}

_t_summary() {
	printf '\n%s: %d passed, %d failed\n' "$(basename "$0")" "$PASS" "$FAIL"
	[[ $FAIL -eq 0 ]]
}

TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TEST_TMPDIR}"' EXIT

readonly DEV="${TEST_TMPDIR}/device"
readonly FAKE_BIN="${TEST_TMPDIR}/fake_bin"
mkdir -p "${DEV}" "${FAKE_BIN}"

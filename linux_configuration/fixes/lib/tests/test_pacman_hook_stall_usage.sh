#!/usr/bin/env bash
# Tests for lib/pacman_hook_stall_usage.sh: usage.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_harness.sh"

reset_state
# usage() calls `exit`, not `return` -- command substitution already runs it
# in a subshell, so the exit only ends that subshell, not this test script.
out="$(usage 2>&1)"
rc=$?
_t_eq "0" "$rc" "usage: exits 0"

if [[ "$out" == *"Usage: ${SCRIPT_NAME}"* ]]; then
	_t_pass "usage: prints the usage header with SCRIPT_NAME"
else
	_t_fail "usage: expected the usage header, got: $out"
fi

if [[ "$out" == *"--runs"* && "$out" == *"--with-load"* && "$out" == *"--watch"* ]]; then
	_t_pass "usage: documents the runs/with-load/watch flags"
else
	_t_fail "usage: expected --runs, --with-load and --watch documented"
fi

if [[ "$out" == *"default: ${RUNS}"* ]]; then
	_t_pass "usage: interpolates the current RUNS default"
else
	_t_fail "usage: expected 'default: ${RUNS}' in the output"
fi

echo
echo "pacman_hook_stall_usage: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

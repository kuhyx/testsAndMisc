#!/usr/bin/env bash
# Tests for lib/pacman_hook_stall_summary.sh: print_summary.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_harness.sh"

# --- no stalls: prints counts/durations, no "Captured dumps" section -------

reset_state
RUNS=3
STALLS=0
durations=(5 12 8)
out="$(print_summary durations)"

if [[ "$out" == *"transactions : 3"* ]]; then
	_t_pass "print_summary: reports the transaction count"
else
	_t_fail "print_summary: expected 'transactions : 3' in output"
fi

if [[ "$out" == *"stalls       : 0"* ]]; then
	_t_pass "print_summary: reports zero stalls"
else
	_t_fail "print_summary: expected 'stalls       : 0' in output"
fi

if [[ "$out" == *"durations    : 5 12 8"* ]]; then
	_t_pass "print_summary: lists durations in the caller's order"
else
	_t_fail "print_summary: expected 'durations    : 5 12 8' in output"
fi

if [[ "$out" == *"min/median/max: 5s / 8s / 12s"* ]]; then
	_t_pass "print_summary: computes min/median/max for an odd count"
else
	_t_fail "print_summary: expected min/median/max '5s / 8s / 12s' in output"
fi

if [[ "$out" != *"Captured dumps"* ]]; then
	_t_pass "print_summary: omits the dumps section when STALLS is 0"
else
	_t_fail "print_summary: should not print 'Captured dumps' when STALLS is 0"
fi

# --- with stalls: lists the captured dump directories -----------------------

reset_state
RUNS=2
STALLS=2
mkdir -p "${OUT_DIR}/dumpA" "${OUT_DIR}/dumpB"
durations=(21 30)
out="$(print_summary durations)"

if [[ "$out" == *"Captured dumps:"* && "$out" == *"dumpA"* && "$out" == *"dumpB"* ]]; then
	_t_pass "print_summary: lists captured dump directories when STALLS > 0"
else
	_t_fail "print_summary: expected both dump dirs listed, got: $out"
fi

if [[ "$out" == *"min/median/max: 21s / 21s / 30s"* ]]; then
	_t_pass "print_summary: computes the lower-median for an even count"
else
	_t_fail "print_summary: expected min/median/max '21s / 21s / 30s' in output"
fi

# --- a single duration: min == median == max --------------------------------

reset_state
RUNS=1
STALLS=0
durations=(42)
out="$(print_summary durations)"
if [[ "$out" == *"min/median/max: 42s / 42s / 42s"* ]]; then
	_t_pass "print_summary: min/median/max collapse to the same value with one run"
else
	_t_fail "print_summary: expected min/median/max '42s / 42s / 42s' in output"
fi

# --- empty durations: the bash-side count guard doesn't crash ---------------

reset_state
RUNS=0
STALLS=0
durations=()
_t_eq "0" "${#durations[@]}" "print_summary: durations starts empty"
if out="$(print_summary durations 2>&1)"; then
	_t_pass "print_summary: handles an empty durations array without crashing"
else
	_t_fail "print_summary: should not fail on an empty durations array: $out"
fi
if [[ "$out" != *"min/median/max"* ]]; then
	_t_pass "print_summary: omits min/median/max when there are no durations"
else
	_t_fail "print_summary: should not print min/median/max with no durations"
fi

echo
echo "pacman_hook_stall_summary: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

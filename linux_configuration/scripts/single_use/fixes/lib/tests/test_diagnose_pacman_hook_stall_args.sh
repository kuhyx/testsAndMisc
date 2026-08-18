#!/usr/bin/env bash
# Subprocess tests for diagnose_pacman_hook_stall.sh's arg parsing and basic
# run paths: -h, unknown flags, -n 0, -p, --with-load, and a single clean
# -n 1 run (plus the "log advances mid-run" branch of run_one).
#
# See pacman_hook_stall_entry_harness.sh for the fake pacman.orig/run_entry
# setup this sources. The heavier timing tests (stalls, hard-timeout,
# SIGTERM, --watch) live in test_diagnose_pacman_hook_stall_timing.sh --
# split purely to stay under the repo's 250-line file cap.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_entry_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_entry_harness.sh"

# --- -h/--help: exits 0, prints usage, never touches pacman -----------------

out_dir="$(run_entry -h)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "^Usage:" "${out_dir}/stdout"; then
	_t_pass "entry -h: exits 0 and prints usage"
else
	_t_fail "entry -h: expected exit 0 and a usage line, got rc=$rc, stdout: $(cat "${out_dir}/stdout")"
fi

# --- unknown flag: exits 1, no usage ----------------------------------------

out_dir="$(run_entry --nope)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" != "0" ]] && grep -q "Unknown option" "${out_dir}/stderr"; then
	_t_pass "entry --nope: rejects an unknown flag"
else
	_t_fail "entry --nope: expected a nonzero exit and 'Unknown option', got rc=$rc"
fi

# --- -n 0: skip_load path, RUNS=0, print_summary with an empty array -------

out_dir="$(run_entry -n 0)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "transactions : 0" "${out_dir}/stdout"; then
	_t_pass "entry -n 0: completes with zero transactions"
else
	_t_fail "entry -n 0: expected exit 0 and 'transactions : 0', got rc=$rc, stdout: $(cat "${out_dir}/stdout")"
fi

# --- -p/--package: value flows through to the summary banner ---------------

out_dir="$(run_entry -n 0 -p some-other-pkg)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "package     : some-other-pkg" "${out_dir}/stdout"; then
	_t_pass "entry -p: overrides the package name"
else
	_t_fail "entry -p: expected 'package     : some-other-pkg' in stdout, got rc=$rc"
fi

# --- --with-load: allocates a small amount and reports "memory pressure ON" -
#
# LOAD_FLOOR_MB defaults to 800 (allocate "everything down to 800 MB free"),
# which on a real box would dd multiple GB into tmpfs. Pin it well under
# whatever's actually available (a 100 MB margin, not the smallest possible)
# so this test allocates a small, positive amount even if MemAvailable drops
# slightly between this snapshot and start_load's own re-read of it.

avail_mb="$(awk '/MemAvailable/ {print int($2 / 1024)}' /proc/meminfo)"
export LOAD_FLOOR_MB=$((avail_mb - 100))
export LOAD_MIN_FREE_MB=1
out_dir="$(run_entry -n 0 --with-load -t 1 --hard-timeout 2)"
unset LOAD_FLOOR_MB LOAD_MIN_FREE_MB
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "memory pressure ON" "${out_dir}/stdout" &&
	grep -qE "allocating [0-9]{1,3} MB" "${out_dir}/stdout"; then
	_t_pass "entry --with-load: reports memory pressure ON and allocates a small amount"
else
	_t_fail "entry --with-load: expected 'memory pressure ON' and a small allocation, got rc=$rc, stdout: $(cat "${out_dir}/stdout")"
fi

# --- -n 1, fast pacman: one clean run, no stall -----------------------------

out_dir="$(run_entry -n 1 -t 5 --hard-timeout 8)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "stalls       : 0" "${out_dir}/stdout"; then
	_t_pass "entry -n 1 (fast pacman): completes with zero stalls"
else
	_t_fail "entry -n 1 (fast pacman): expected exit 0 and zero stalls, got rc=$rc, stdout: $(cat "${out_dir}/stdout")"
fi

# --- -n 1, pacman.log advances mid-run: run_one's "log advanced, reset the
#     silence timer" branch fires and no stall is captured -----------------

out_dir="$(run_entry --log-advance-at 1 -n 1 -t 5 --hard-timeout 8)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "stalls       : 0" "${out_dir}/stdout"; then
	_t_pass "entry -n 1 (log advances mid-run): log activity resets the silence timer"
else
	_t_fail "entry -n 1 (log advances): expected exit 0 and zero stalls, got rc=$rc, stdout: $(cat "${out_dir}/stdout")"
fi

echo
echo "diagnose_pacman_hook_stall (args): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

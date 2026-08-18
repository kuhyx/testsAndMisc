#!/usr/bin/env bash
# Tests for lib/pacman_hook_stall_load.sh: mem_available_mb, start_load,
# stop_load.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_harness.sh"

# --- mem_available_mb ---------------------------------------------------------

reset_state
got="$(mem_available_mb)"
if [[ "$got" =~ ^[0-9]+$ && "$got" -gt 0 ]]; then
	_t_pass "mem_available_mb: reads a positive integer from /proc/meminfo"
else
	_t_fail "mem_available_mb: expected a positive integer, got '$got'"
fi

# --- start_load / stop_load: WITH_LOAD=0 is a no-op ---------------------------

reset_state
WITH_LOAD=0
if (start_load) && [[ -z "$HOG_FILE" ]]; then
	_t_pass "start_load: no-ops when WITH_LOAD=0"
else
	_t_fail "start_load: should no-op (and not set HOG_FILE) when WITH_LOAD=0"
fi

# --- start_load: refuses when available memory is below LOAD_MIN_FREE_MB ------

reset_state
WITH_LOAD=1
avail="$(mem_available_mb)"
LOAD_MIN_FREE_MB=$((avail + 100000))
if (start_load) 2>/dev/null; then
	_t_fail "start_load: should refuse when available < LOAD_MIN_FREE_MB"
else
	_t_pass "start_load: refuses when available < LOAD_MIN_FREE_MB"
fi

# --- start_load: allocates (a tiny amount) and stop_load cleans it up ---------

reset_state
WITH_LOAD=1
avail="$(mem_available_mb)"
LOAD_MIN_FREE_MB=1
LOAD_FLOOR_MB=$((avail - 2))
(
	start_load
	[[ -n "$HOG_FILE" && -e "$HOG_FILE" ]] || exit 1
	echo "$HOG_FILE" >"${DEV}/hog_file_path"
)
if [[ -f "${DEV}/hog_file_path" ]]; then
	_t_pass "start_load: allocates and sets HOG_FILE when under the floor"
else
	_t_fail "start_load: should allocate and set HOG_FILE"
fi

reset_state
WITH_LOAD=1
avail="$(mem_available_mb)"
LOAD_MIN_FREE_MB=1
LOAD_FLOOR_MB=$((avail - 2))
start_load
hog="$HOG_FILE"
stop_load
if [[ -n "$hog" && ! -e "$hog" && -z "$HOG_FILE" ]]; then
	_t_pass "stop_load: removes HOG_FILE and clears the variable"
else
	_t_fail "stop_load: expected HOG_FILE removed and cleared, got '$HOG_FILE' (file existed: $([[ -e "$hog" ]] && echo yes || echo no))"
fi

# --- stop_load: kills LOAD_PID if still alive ----------------------------------

reset_state
/usr/bin/sleep 60 &
LOAD_PID=$!
# Without job control (the default for a non-interactive script), SIGTERM to
# a background job can race the shell's own handling of it; disown detaches
# the job from shell bookkeeping so the kill below only affects the child.
disown "$LOAD_PID" 2>/dev/null || true
stop_load
still_alive=1
for _ in $(seq 1 20); do
	kill -0 "$LOAD_PID" 2>/dev/null || {
		still_alive=0
		break
	}
	/usr/bin/sleep 0.1
done
if ((still_alive == 0)); then
	_t_pass "stop_load: kills a live LOAD_PID"
else
	_t_fail "stop_load: LOAD_PID should have been killed"
	kill -9 "$LOAD_PID" 2>/dev/null || true
fi
wait "$LOAD_PID" 2>/dev/null || true

# --- stop_load: no-ops cleanly with no HOG_FILE/LOAD_PID set -------------------

reset_state
if (stop_load); then
	_t_pass "stop_load: no-ops cleanly when nothing was started"
else
	_t_fail "stop_load: should not fail with nothing to clean up"
fi

echo
echo "pacman_hook_stall_load: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

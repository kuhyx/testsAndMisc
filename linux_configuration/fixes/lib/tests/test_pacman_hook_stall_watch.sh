#!/usr/bin/env bash
# Tests for lib/pacman_hook_stall_watch.sh: watch_forever.
#
# watch_forever is `while true`, and its bare `sleep 1` inside the loop
# doesn't check sleep's exit status -- so the fake sleep's exit-after-N-calls
# lever can't break the loop from the inside when the call is guarded by
# `|| true` (that suppresses `set -e` for the whole function, not just its
# last statement). Instead: background it, let it run for a fixed real-time
# window, then kill it and assert on what it left behind ($DEV/calls,
# $OUT_DIR dump dirs) -- STALLS itself doesn't propagate out of a background
# subshell.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_harness.sh"

# run_watch_for SECONDS — start watch_forever in the background, let it run
# for SECONDS of wall-clock time (using the real sleep, not the fake one),
# then kill it. Dump directories and $DEV/calls reflect whatever it did.
run_watch_for() {
	local secs="$1"
	watch_forever >/dev/null 2>&1 &
	local wpid=$!
	disown "$wpid" 2>/dev/null || true
	/usr/bin/sleep "$secs"
	kill -9 "$wpid" 2>/dev/null || true
	wait "$wpid" 2>/dev/null || true
}

dump_count() { find "${OUT_DIR}" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l; }

# --- log stays silent, no live pacman -> no stall captured ------------------

reset_state
: >"${PACMAN_LOG}"
STALL_TIMEOUT=1
run_watch_for 2
_t_eq "0" "$(dump_count)" "watch_forever: no stall captured when pgrep finds nothing"

# --- log silent AND a matching pacman pid -> captures, and logs it ----------

reset_state
: >"${PACMAN_LOG}"
STALL_TIMEOUT=1
echo "$$" >"${DEV}/pgrep_pid"
run_watch_for 2
count="$(dump_count)"
if ((count >= 1)); then
	_t_pass "watch_forever: captures a stall when pgrep finds a live pacman"
else
	_t_fail "watch_forever: expected at least one dump dir, got $count"
fi

if grep -q "captured a stalled transaction" "${DEV}/calls" 2>/dev/null; then
	_t_pass "watch_forever: logs the capture via logger"
else
	_t_fail "watch_forever: expected a logger call recording the capture"
fi

# --- once armed, stays armed while still silent: no re-capture -------------

reset_state
: >"${PACMAN_LOG}"
STALL_TIMEOUT=1
echo "$$" >"${DEV}/pgrep_pid"
run_watch_for 3
count="$(dump_count)"
_t_eq "1" "$count" "watch_forever: re-arms only after log activity, not every idle tick"

# --- log activity resets the silence timer: no capture with a high timeout -

reset_state
: >"${PACMAN_LOG}"
STALL_TIMEOUT=100
echo "$$" >"${DEV}/pgrep_pid"
watch_forever >/dev/null 2>&1 &
wpid=$!
disown "$wpid" 2>/dev/null || true
/usr/bin/sleep 0.5
echo "line" >>"${PACMAN_LOG}"
/usr/bin/sleep 1
kill -9 "$wpid" 2>/dev/null || true
wait "$wpid" 2>/dev/null || true
_t_eq "0" "$(dump_count)" "watch_forever: log activity prevents a capture"

echo
echo "pacman_hook_stall_watch: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

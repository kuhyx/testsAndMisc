#!/usr/bin/env bash
# Tests for lib/pacman_hook_stall_capture.sh: descendant_pids, kill_tree,
# capture_stall.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_harness.sh"

# --- descendant_pids -----------------------------------------------------------

reset_state
# ps_tree format: "parent:child" lines, one per fake `ps -o pid= --ppid`.
cat >"${DEV}/ps_tree" <<'EOF'
100:200
100:201
200:300
EOF
got="$(descendant_pids 100 | sort -n | tr '\n' ' ')"
_t_eq "100 200 201 300 " "$got" \
	"descendant_pids: walks the whole tree breadth-first, includes the root"

reset_state
got="$(descendant_pids 500 | tr '\n' ' ')"
_t_eq "500 " "$got" \
	"descendant_pids: a childless root prints only itself"

# --- kill_tree -------------------------------------------------------------

reset_state
/usr/bin/sleep 60 &
parent=$!
disown "$parent" 2>/dev/null || true
/usr/bin/sleep 60 &
child=$!
disown "$child" 2>/dev/null || true
printf '%s:%s\n' "$parent" "$child" >"${DEV}/ps_tree"
kill_tree "$parent"
still_alive=0
for _ in $(seq 1 20); do
	kill -0 "$parent" 2>/dev/null && still_alive=$((still_alive + 1))
	kill -0 "$child" 2>/dev/null && still_alive=$((still_alive + 1))
	((still_alive == 0)) && break
	still_alive=0
	/usr/bin/sleep 0.1
done
if ! kill -0 "$parent" 2>/dev/null && ! kill -0 "$child" 2>/dev/null; then
	_t_pass "kill_tree: kills the root and every descendant"
else
	_t_fail "kill_tree: expected both root and child dead"
	kill -9 "$parent" "$child" 2>/dev/null || true
fi

reset_state
if (kill_tree 999999); then
	_t_pass "kill_tree: a nonexistent root is a harmless no-op"
else
	_t_fail "kill_tree: should not fail on a nonexistent PID"
fi

# --- capture_stall -----------------------------------------------------------

reset_state
printf 'some earlier line\n' >>"${PACMAN_LOG}"
printf "running 'guard-lib.hook'...\n" >>"${PACMAN_LOG}"
STALLS=0
capture_stall $$ 1
dump_dir="$(find "${OUT_DIR}" -mindepth 1 -maxdepth 1 -type d | head -1)"
if [[ -n "$dump_dir" && "$dump_dir" == *-run1-hook ]]; then
	_t_pass "capture_stall: classifies a hook-line stall and names the dump dir accordingly"
else
	_t_fail "capture_stall: expected a *-run1-hook dump dir, got '$dump_dir'"
fi
_t_eq "1" "$STALLS" "capture_stall: increments STALLS"

reset_state
printf 'unrelated log line\n' >>"${PACMAN_LOG}"
STALLS=0
capture_stall $$ 2
dump_dir="$(find "${OUT_DIR}" -mindepth 1 -maxdepth 1 -type d | head -1)"
if [[ -n "$dump_dir" && "$dump_dir" == *-run2-other ]]; then
	_t_pass "capture_stall: classifies a non-hook stall as 'other'"
else
	_t_fail "capture_stall: expected a *-run2-other dump dir, got '$dump_dir'"
fi

reset_state
printf 'x\n' >>"${PACMAN_LOG}"
capture_stall $$ 3
dump_dir="$(find "${OUT_DIR}" -mindepth 1 -maxdepth 1 -type d | head -1)"
if [[ -f "${dump_dir}/procs.txt" && -f "${dump_dir}/meminfo.txt" &&
	-f "${dump_dir}/pressure.txt" && -f "${dump_dir}/dmesg-tail.txt" &&
	-f "${dump_dir}/pacman-log-tail.txt" && -f "${dump_dir}/last-log-line.txt" &&
	-f "${dump_dir}/ps-forest.txt" ]]; then
	_t_pass "capture_stall: writes every expected diagnostic file"
else
	_t_fail "capture_stall: missing one or more expected diagnostic files in $dump_dir"
	ls -la "$dump_dir" 2>&1
fi

echo
echo "pacman_hook_stall_capture: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

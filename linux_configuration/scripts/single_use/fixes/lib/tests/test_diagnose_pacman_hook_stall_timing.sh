#!/usr/bin/env bash
# Subprocess tests for diagnose_pacman_hook_stall.sh's timing-sensitive
# paths: a real stall capture, the hard-timeout kill, cleanup's kill_tree
# branch on SIGTERM, and --watch mode.
#
# See pacman_hook_stall_entry_harness.sh for the fake pacman.orig/run_entry
# setup this sources. Arg-parsing and other basic run paths live in
# test_diagnose_pacman_hook_stall_args.sh -- split purely to stay under the
# repo's 250-line file cap.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pacman_hook_stall_entry_harness.sh
. "${SCRIPT_DIR}/pacman_hook_stall_entry_harness.sh"

# --- -n 1 with a real stall: pacman hangs past STALL_TIMEOUT but returns
#     before HARD_TIMEOUT -- one stall captured, run still completes --------

out_dir="$(run_entry --hang 3 -n 1 -t 1 --hard-timeout 8)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "stalls       : 1" "${out_dir}/stdout"; then
	_t_pass "entry -n 1 (pacman hangs 3s, timeout 1s): captures exactly one stall"
else
	_t_fail "entry -n 1 (stall): expected exit 0 and one stall, got rc=$rc, stdout: $(cat "${out_dir}/stdout")"
fi
if [[ -d "${out_dir}/dumps" ]] && [[ -n "$(find "${out_dir}/dumps" -mindepth 1 -maxdepth 1 -type d)" ]]; then
	_t_pass "entry -n 1 (stall): writes a dump directory under -o"
else
	_t_fail "entry -n 1 (stall): expected a dump directory under ${out_dir}/dumps"
fi

# --- -n 1 with hard-timeout: pacman hangs past HARD_TIMEOUT, gets killed ----

out_dir="$(run_entry --hang 20 -n 1 -t 1 --hard-timeout 2)"
rc="$(cat "${out_dir}/rc")"
if [[ "$rc" == "0" ]] && grep -q "hard timeout" "${out_dir}/stdout"; then
	_t_pass "entry -n 1 (hard timeout): kills the stuck transaction and reports it"
else
	_t_fail "entry -n 1 (hard timeout): expected a 'hard timeout' line, got rc=$rc, stdout: $(cat "${out_dir}/stdout")"
fi

# --- SIGTERM mid-run: cleanup's kill_tree branch fires on a live PACMAN_PID.
#     Uses TERM, not INT: the entry script's `trap cleanup EXIT INT TERM`
#     wires both to the same handler, and INT delivery to a backgrounded job
#     was observed to be unreliable in this environment while TERM is not.

out_dir="$(run_entry --background --hang 30 -n 5 -t 100 --hard-timeout 100)"
pid="$(cat "${out_dir}/pid")"
disown "$pid" 2>/dev/null || true
/usr/bin/sleep 1
kill -TERM "$pid" 2>/dev/null || true
for _ in $(seq 1 30); do
	grep -q "Cleaning up: killing in-flight pacman" "${out_dir}/stderr" 2>/dev/null && break
	/usr/bin/sleep 0.2
done
wait "$pid" 2>/dev/null || true
if grep -q "Cleaning up: killing in-flight pacman" "${out_dir}/stderr"; then
	_t_pass "entry SIGTERM mid-run: cleanup kills the in-flight pacman transaction"
else
	_t_fail "entry SIGTERM mid-run: expected the cleanup message on stderr, got: $(cat "${out_dir}/stderr")"
fi

# --- --watch: runs the passive watcher; kill it and confirm it started -----

out_dir="$(run_entry --background --watch)"
pid="$(cat "${out_dir}/pid")"
/usr/bin/sleep 1.5
if kill -0 "$pid" 2>/dev/null; then
	_t_pass "entry --watch: stays running (doesn't exit early)"
else
	_t_fail "entry --watch: exited early, stdout: $(cat "${out_dir}/stdout" 2>/dev/null)"
fi
kill -9 "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
if grep -q "^Watching" "${out_dir}/stdout" 2>/dev/null; then
	_t_pass "entry --watch: prints the watching banner"
else
	_t_fail "entry --watch: expected a 'Watching' banner in stdout"
fi

echo
echo "diagnose_pacman_hook_stall (timing): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

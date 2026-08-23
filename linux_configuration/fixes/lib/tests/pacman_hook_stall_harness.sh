#!/usr/bin/env bash
# lib/tests/pacman_hook_stall_harness.sh — fake pacman/ps/journalctl/pgrep/
# logger/sleep behind the diagnose_pacman_hook_stall.sh split.
#
# Sourced, not executed. Every external tool the script calls is a shim on
# PATH that records its invocation into $DEV and does the minimum real
# filesystem work the calling code depends on. PACMAN_BIN, PACMAN_LOG,
# CACHE_DIR and PACMAN_LOCK all point into a throwaway tmpdir (via the
# env-overridable globals the split introduced) so nothing touches the real
# machine.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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
	local want="$1" got="$2" what="$3"
	if [[ "$got" == "$want" ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (want '${want}', got '${got}')"
	fi
}

TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TEST_TMPDIR}"' EXIT

readonly DEV="${TEST_TMPDIR}/device"
readonly FAKE_BIN="${TEST_TMPDIR}/fake_bin"
mkdir -p "${DEV}" "${FAKE_BIN}"

# --- fake external tools ----------------------------------------------------

# Fake pacman.orig: `-Q <pkg>` reports an installed version (or "fail_query"
# to simulate not-installed), `-U --noconfirm <file>` simulates a transaction
# that either finishes fast or hangs until killed (via "$DEV/hang_seconds").
cat >"${FAKE_BIN}/pacman.orig" <<'PACMANSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${STALL_TEST_DEV}"
printf '%s\n' "pacman.orig $*" >>"${DEV}/calls"
if [[ "$1" == "-Q" ]]; then
	if [[ -f "${DEV}/fail_query" ]]; then
		exit 1
	fi
	printf '%s %s\n' "$2" "1.2.3-1"
	exit 0
fi
if [[ "$1" == "-U" ]]; then
	hang=0
	[[ -f "${DEV}/hang_seconds" ]] && hang="$(cat "${DEV}/hang_seconds")"
	trap 'exit 0' TERM INT
	sleep "$hang"
	exit 0
fi
exit 0
PACMANSHIM
chmod +x "${FAKE_BIN}/pacman.orig"

# Fake ps: only the two invocation shapes the code uses.
#   ps -o pid= --ppid <pid>   -> children of <pid>, from $DEV/ps_tree
#   ps -eo ... --forest       -> a static one-line snapshot
cat >"${FAKE_BIN}/ps" <<'PSSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${STALL_TEST_DEV}"
if [[ "$1" == "-o" && "$2" == "pid=" && "$3" == "--ppid" ]]; then
	parent="$4"
	[[ -f "${DEV}/ps_tree" ]] || exit 0
	awk -F: -v p="$parent" '$1 == p { print $2 }' "${DEV}/ps_tree"
	exit 0
fi
echo "  PID  PPID STAT WCHAN                              ELAPSED COMMAND"
exit 0
PSSHIM
chmod +x "${FAKE_BIN}/ps"

cat >"${FAKE_BIN}/journalctl" <<'JOURNALSHIM'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "journalctl $*" >>"${STALL_TEST_DEV}/calls"
echo "fake kernel log line"
exit 0
JOURNALSHIM
chmod +x "${FAKE_BIN}/journalctl"

# Fake pgrep -x pacman.orig: reports the PID recorded in $DEV/pgrep_pid, or
# nothing (real pgrep exits 1 on no match).
cat >"${FAKE_BIN}/pgrep" <<'PGREPSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${STALL_TEST_DEV}"
printf '%s\n' "pgrep $*" >>"${DEV}/calls"
if [[ -f "${DEV}/pgrep_pid" ]]; then
	cat "${DEV}/pgrep_pid"
	exit 0
fi
exit 1
PGREPSHIM
chmod +x "${FAKE_BIN}/pgrep"

cat >"${FAKE_BIN}/logger" <<'LOGGERSHIM'
#!/usr/bin/env bash
printf '%s\n' "logger $*" >>"${STALL_TEST_DEV}/calls"
exit 0
LOGGERSHIM
chmod +x "${FAKE_BIN}/logger"

# Fake sleep: records calls and, after $DEV/sleep_exit_after calls, exits
# non-zero so an infinite `while true; do sleep 1; ...; done` loop
# (watch_forever) terminates instead of hanging the test suite.
cat >"${FAKE_BIN}/sleep" <<'SLEEPSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${STALL_TEST_DEV}"
count_file="${DEV}/sleep_count"
[[ -f "$count_file" ]] || echo 0 >"$count_file"
n=$(($(cat "$count_file") + 1))
echo "$n" >"$count_file"
if [[ -f "${DEV}/sleep_exit_after" ]]; then
	limit="$(cat "${DEV}/sleep_exit_after")"
	if ((n > limit)); then
		exit 1
	fi
fi
exit 0
SLEEPSHIM
chmod +x "${FAKE_BIN}/sleep"

export STALL_TEST_DEV="${DEV}"
export PATH="${FAKE_BIN}:${PATH}"

# --- subject under test -----------------------------------------------------

export PACMAN_BIN="${FAKE_BIN}/pacman.orig"
export PACMAN_LOG="${TEST_TMPDIR}/pacman.log"
export CACHE_DIR="${TEST_TMPDIR}/cache"
export PACMAN_LOCK="${TEST_TMPDIR}/db.lck"
: >"${PACMAN_LOG}"
mkdir -p "${CACHE_DIR}"

# shellcheck source=../pacman_hook_stall_setup.sh
. "${FIXES_DIR}/lib/pacman_hook_stall_setup.sh"
# shellcheck source=../pacman_hook_stall_load.sh
. "${FIXES_DIR}/lib/pacman_hook_stall_load.sh"
# shellcheck source=../pacman_hook_stall_capture.sh
. "${FIXES_DIR}/lib/pacman_hook_stall_capture.sh"
# shellcheck source=../pacman_hook_stall_watch.sh
. "${FIXES_DIR}/lib/pacman_hook_stall_watch.sh"
# shellcheck source=../pacman_hook_stall_usage.sh
. "${FIXES_DIR}/lib/pacman_hook_stall_usage.sh"
# shellcheck source=../pacman_hook_stall_summary.sh
. "${FIXES_DIR}/lib/pacman_hook_stall_summary.sh"

# log_size lives in the entry script itself (diagnose_pacman_hook_stall.sh),
# not in a lib -- moving it would reintroduce the LAST_ELAPSED/PACMAN_BIN
# cross-file-global seam the split was designed to avoid. Redefined here
# verbatim so run_one()/watch_forever() (called directly from tests) resolve
# it exactly as they do when sourced from the real entry script.
log_size() { stat -c %s "$PACMAN_LOG" 2>/dev/null || echo 0; }

# Globals the six libs read. run_one()/main()/cleanup() (which additionally
# read WATCH_MODE/RUN_INDEX/LAST_ELAPSED/PACMAN_PID) live in the entry
# script, not a lib -- test_diagnose_pacman_hook_stall.sh exercises those
# directly as a subprocess instead, so this harness only needs what the libs
# themselves reference.
SCRIPT_NAME="diagnose_pacman_hook_stall.sh"
RUNS=40
PACKAGE="base-devel"
STALL_TIMEOUT=20
HARD_TIMEOUT=120
OUT_DIR="${TEST_TMPDIR}/out"
WITH_LOAD=0
LOAD_FLOOR_MB=800
LOAD_MIN_FREE_MB=1500
HOG_FILE=""
LOAD_PID=""
STALLS=0

# reset_state — wipe DEV/OUT_DIR/PACMAN_LOG between test groups so each group
# starts from "nothing has happened yet".
reset_state() {
	rm -rf "${OUT_DIR}" "${DEV:?}/calls" "${DEV}/hang_seconds" "${DEV}/ps_tree" \
		"${DEV}/pgrep_pid" "${DEV}/sleep_count" "${DEV}/sleep_exit_after" \
		"${DEV}/fail_query" 2>/dev/null || true
	: >"${PACMAN_LOG}"
	: >"${DEV}/calls"
	STALLS=0
	HOG_FILE=""
	LOAD_PID=""
}
reset_state

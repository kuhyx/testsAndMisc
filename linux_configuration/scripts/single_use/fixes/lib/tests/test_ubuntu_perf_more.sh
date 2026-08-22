#!/usr/bin/env bash
# Tests for lib/ubuntu_perf_more.sh: fix_journal, fix_snap_startup and run_undo.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ubuntu_perf_harness.sh
. "${SCRIPT_DIR}/ubuntu_perf_harness.sh"

# shellcheck source=../ubuntu_perf_more.sh
. "${FIXES_DIR}/lib/ubuntu_perf_more.sh"

# --- fix_journal ------------------------------------------------------------

# First run: the drop-in does not exist, so it is written and journald
# restarted. JOURNALD_CONF_DIR points into the tmpdir, so /etc is untouched.
ubuntu_reset
fix_journal
dropin="${JOURNALD_CONF_DIR}/size-limit.conf"
_t_contains "$(cat "$dropin" 2>/dev/null)" "SystemMaxUse=300M" \
	"fix_journal: writes the 300M size cap into the journald drop-in"
_t_contains "$(cat "$dropin" 2>/dev/null)" "[Journal]" \
	"fix_journal: writes a valid [Journal] section header"
_t_contains "$(_t_calls)" "journalctl --vacuum-size=300M" \
	"fix_journal: vacuums the existing journal down to the cap"
_t_contains "$(_t_calls)" "systemctl restart systemd-journald" \
	"fix_journal: restarts journald so the cap takes effect"
_t_contains "$(_t_undo)" "rm -f /etc/systemd/journald.conf.d/size-limit.conf" \
	"fix_journal: records how to remove the drop-in in the undo script"
_t_contains "$(_t_undo)" "systemctl restart systemd-journald" \
	"fix_journal: records the journald restart in the undo script"

# Second run with the cap already in place: nothing is rewritten.
ubuntu_reset
mkdir -p "${JOURNALD_CONF_DIR}"
printf '[Journal]\nSystemMaxUse=300M\n' >"${JOURNALD_CONF_DIR}/size-limit.conf"
out="$(fix_journal 2>&1)"
_t_contains "$out" "already configured" \
	"fix_journal: skips when the size cap is already configured"
_t_eq "" "$(_t_calls)" "fix_journal: runs no command when the cap already exists"
_t_eq "" "$(_t_undo)" "fix_journal: adds no undo step when it changed nothing"

# A drop-in that exists but caps a DIFFERENT size is rewritten.
ubuntu_reset
mkdir -p "${JOURNALD_CONF_DIR}"
printf '[Journal]\nSystemMaxUse=1G\n' >"${JOURNALD_CONF_DIR}/size-limit.conf"
fix_journal
_t_contains "$(cat "${JOURNALD_CONF_DIR}/size-limit.conf")" "SystemMaxUse=300M" \
	"fix_journal: rewrites a drop-in that caps a different size"

# --- fix_snap_startup -------------------------------------------------------

# The timer is enabled: it gets disabled and stopped, and an undo recorded.
ubuntu_reset
_t_stub systemctl 'exit 0'
fix_snap_startup
_t_contains "$(_t_calls)" "systemctl disable snapd.snap-repair.timer" \
	"fix_snap_startup: disables the snap repair timer when it is enabled"
_t_contains "$(_t_calls)" "systemctl stop snapd.snap-repair.timer" \
	"fix_snap_startup: stops the snap repair timer as well as disabling it"
_t_contains "$(_t_undo)" "systemctl enable snapd.snap-repair.timer" \
	"fix_snap_startup: records how to re-enable the timer in the undo script"

# Already disabled: nothing to do.
ubuntu_reset
_t_stub systemctl 'exit 1'
out="$(fix_snap_startup 2>&1)"
_t_contains "$out" "already disabled" \
	"fix_snap_startup: reports a timer that is already disabled"
_t_lacks "$(_t_calls)" "systemctl disable" \
	"fix_snap_startup: does not re-disable an already-disabled timer"
_t_eq "" "$(_t_undo)" "fix_snap_startup: adds no undo step when it changed nothing"

# --- run_undo ---------------------------------------------------------------
#
# run_undo ends in `exit`, so each case runs it in a subshell -- a command
# substitution already provides one, and the exit only ends that subshell.
# UNDO_DIR points into the tmpdir, so the real /root is never read.

ubuntu_reset
out="$( (run_undo) 2>&1)"
rc=$?
_t_eq "1" "$rc" "run_undo: exits non-zero when no undo script exists"
_t_contains "$out" "No undo script found" \
	"run_undo: reports that no undo script was found"

ubuntu_reset
cat >"${UNDO_DIR}/undo_ubuntu_performance_20260101_000000.sh" <<'UNDO'
#!/bin/bash
echo "undo script ran"
UNDO
out="$( (run_undo) 2>&1)"
rc=$?
_t_eq "0" "$rc" "run_undo: exits 0 after running the undo script"
_t_contains "$out" "undo script ran" "run_undo: actually executes the undo script"
_t_contains "$out" "All changes reversed" "run_undo: reports success"
_t_contains "$out" "Reboot recommended" "run_undo: recommends a reboot afterwards"

# With several undo scripts present, the most recent one is chosen.
ubuntu_reset
echo 'echo "older"' >"${UNDO_DIR}/undo_ubuntu_performance_20260101_000000.sh"
sleep 0.01
echo 'echo "newest"' >"${UNDO_DIR}/undo_ubuntu_performance_20260601_120000.sh"
touch -d '2026-01-01' "${UNDO_DIR}/undo_ubuntu_performance_20260101_000000.sh"
out="$( (run_undo) 2>&1)"
_t_contains "$out" "newest" "run_undo: picks the most recent undo script"
_t_lacks "$out" "older" "run_undo: does not run an older undo script"

echo
echo "ubuntu_perf_more: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))

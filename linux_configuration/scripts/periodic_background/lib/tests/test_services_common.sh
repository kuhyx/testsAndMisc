#!/usr/bin/env bash
# Tests for lib/services_common.sh — output helpers, the status store, the
# dry-run `run` gate, deployment_drift, the guard-lib probe and report_and_fix.
#
# report_and_fix is the one with real branching: status ok vs warning vs error,
# STATUS_ONLY on/off, installer present/missing, and the post-fix re-verify that
# can promote a status to "ok". Each combination gets its own case.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"

echo "== output helpers =="
reset_state
_t_eq "1" "$(msg yes | grep -c 'yes')" "msg prints its argument"
_t_eq "1" "$(note hi | grep -c 'hi')" "note prints its argument"
_t_eq "1" "$(warn hi | grep -c 'hi')" "warn prints its argument"
_t_eq "1" "$(err hi | grep -c 'hi')" "err prints its argument"
_t_eq "1" "$(header hi | grep -c 'hi')" "header prints its argument"

echo "== err_missing_script records and logs =="
reset_state
err_missing_script "missing: /nope/install.sh" >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "the missing script is recorded"
_t_called 'logger .*MISSING REPAIR SCRIPT' "the miss is logged at error priority"

echo "== status store =="
reset_state
_t_eq "unknown" "$(get_service_status "nothing_set")" "unset key reads as unknown"
set_service_status "hosts" "ok"
_t_eq "ok" "$(get_service_status "hosts")" "a recorded status reads back"
# A second write to one key means two checks are fighting over one summary row.
if set_service_status "hosts" "error" >/dev/null 2>&1; then
	_t_fail "a duplicate write is rejected"
else
	_t_pass "a duplicate write is rejected"
fi
_t_eq "ok" "$(get_service_status "hosts")" "the rejected write did not overwrite"

echo "== run honours --dry-run =="
reset_state
DRY_RUN=1
out="$(run logger would-have-run)"
_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}
_t_called_in "$out" "DRY-RUN:" "dry-run announces instead of running"
_t_not_called 'logger would-have-run' "dry-run did not actually run the command"
DRY_RUN=0
run logger really-ran
_t_called 'logger really-ran' "with dry-run off the command really runs"

echo "== user_systemctl targets the user bus =="
reset_state
printf 'user:workout-locker.service\n' >"${DEV}/enabled"
if user_systemctl kuhy is-enabled workout-locker.service; then
	_t_pass "user_systemctl reports an enabled user unit"
else
	_t_fail "user_systemctl reports an enabled user unit"
fi
_t_called 'systemctl --user --machine=kuhy@.host' "it connects via --machine, not sudo -u"

echo "== guard_lib_instance_healthy =="
reset_state
printf 'hosts\n' >"${DEV}/guard_healthy"
printf 'nsswitch\n' >"${DEV}/guard_degraded"
if guard_lib_instance_healthy hosts; then
	_t_pass "a healthy instance passes"
else
	_t_fail "a healthy instance passes"
fi
if guard_lib_instance_healthy nsswitch; then
	_t_fail "an inactive path unit fails"
else
	_t_pass "an inactive path unit fails"
fi
if guard_lib_instance_healthy resolved; then
	_t_fail "an unregistered instance fails"
else
	_t_pass "an unregistered instance fails"
fi

echo "== deployment_drift =="
reset_state
manifest="${TEST_TMPDIR}/drift.sha256"
subject="${TEST_TMPDIR}/subject.txt"
printf 'original\n' >"$subject"
(cd "${TEST_TMPDIR}" && sha256sum "$(basename "$subject")" >"$manifest")
rc=0
(cd "${TEST_TMPDIR}" && deployment_drift "$manifest") || rc=$?
_t_eq "0" "$rc" "a matching manifest verifies"
printf 'tampered\n' >"$subject"
rc=0
(cd "${TEST_TMPDIR}" && deployment_drift "$manifest") || rc=$?
_t_eq "1" "$rc" "an edited file is reported as drift"
rc=0
deployment_drift "${TEST_TMPDIR}/absent.sha256" || rc=$?
_t_eq "2" "$rc" "a missing manifest is 'unverifiable', not a pass"

echo "== report_and_fix: an ok service is recorded and left alone =="
reset_state
declare -a issues=()
status="ok"
report_and_fix issues status "startup_monitor" "fixing..." "$STARTUP_MONITOR_SCRIPT" "" >/dev/null
_t_eq "ok" "$(get_service_status "startup_monitor")" "an ok status is recorded"
_t_eq "0" "$ISSUES_FOUND" "an ok service counts no issues"
_t_not_called 'ran setup_pc' "an ok service runs no installer"

echo "== report_and_fix: a warning is reported but never repaired =="
reset_state
make_installer "$STARTUP_MONITOR_SCRIPT"
issues=("timer is not active")
status="warning"
# Captured to a file rather than `$(...)`: report_and_fix mutates ISSUES_FOUND
# and SERVICE_STATUS, and a command substitution would strand both in a
# subshell, making the assertions below silently test nothing.
report_and_fix issues status "startup_monitor" "fixing..." \
	"$STARTUP_MONITOR_SCRIPT" "" >"${TEST_TMPDIR}/out.txt"
out="$(cat "${TEST_TMPDIR}/out.txt")"
_t_called_in "$out" "timer is not active" "the warning text is printed"
_t_eq "1" "$ISSUES_FOUND" "a warning counts as an issue"
_t_not_called 'ran setup_pc' "a warning does not trigger the installer"
_t_eq "warning" "$(get_service_status "startup_monitor")" "the warning status is recorded"

echo "== report_and_fix: --status reports errors without repairing =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
STATUS_ONLY=1
issues=("timer is not enabled")
status="error"
report_and_fix issues status "periodic_systems" "fixing..." "$PERIODIC_SYSTEM_SCRIPT" "" >/dev/null
_t_not_called 'ran setup_periodic' "--status never runs an installer"
_t_eq "error" "$(get_service_status "periodic_systems")" "the error status survives --status"

echo "== report_and_fix: an error runs the installer and re-verifies =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
printf 'periodic-system-maintenance.timer\n' >"${DEV}/enabled"
issues=("timer is not enabled")
status="error"
report_and_fix issues status "periodic_systems" "fixing..." \
	"$PERIODIC_SYSTEM_SCRIPT" "periodic-system-maintenance.timer" >/dev/null
_t_called 'ran setup_periodic_system' "the installer ran"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"
_t_eq "ok" "$(get_service_status "periodic_systems")" "a unit enabled after the fix is promoted to ok"

echo "== report_and_fix: a fix that does not take leaves the error standing =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
: >"${DEV}/enabled" # the installer ran but the unit is still not enabled
issues=("timer is not enabled")
status="error"
report_and_fix issues status "periodic_systems" "fixing..." \
	"$PERIODIC_SYSTEM_SCRIPT" "periodic-system-maintenance.timer" >/dev/null
_t_called 'ran setup_periodic_system' "the installer ran"
_t_eq "error" "$(get_service_status "periodic_systems")" "an unverified fix does not become ok"

echo "== report_and_fix: dry-run skips the re-verify =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
printf 'periodic-system-maintenance.timer\n' >"${DEV}/enabled"
DRY_RUN=1
issues=("timer is not enabled")
status="error"
report_and_fix issues status "periodic_systems" "fixing..." \
	"$PERIODIC_SYSTEM_SCRIPT" "periodic-system-maintenance.timer" >/dev/null
_t_not_called 'ran setup_periodic_system' "dry-run does not really install"
_t_eq "error" "$(get_service_status "periodic_systems")" "dry-run never claims a fix landed"

echo "== report_and_fix: a missing installer is a broken-self-repair error =="
reset_state
rm -f "$MIDNIGHT_SHUTDOWN_SCRIPT"
issues=("timer is not enabled")
status="error"
report_and_fix issues status "midnight_shutdown" "fixing..." \
	"$MIDNIGHT_SHUTDOWN_SCRIPT" "day-specific-shutdown.timer" >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "the missing installer is recorded"
_t_called 'logger .*MISSING REPAIR SCRIPT' "the missing installer is logged"

echo "== report_and_fix: extra arguments reach the installer =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
issues=("timer is not enabled")
status="error"
report_and_fix issues status "midnight_shutdown" "fixing..." \
	"$MIDNIGHT_SHUTDOWN_SCRIPT" "day-specific-shutdown.timer" enable >/dev/null
_t_called 'ran setup_midnight_shutdown.sh enable' "the trailing args are forwarded"
# report_and_fix rewrites `status` through its nameref; reading it back both
# asserts that and gives shellcheck the read it cannot infer through the
# nameref (SC2034). The unit is not in $DEV/enabled, so the fix cannot verify.
_t_eq "error" "$status" "an unverified fix leaves the caller's status at error"
_t_eq "1" "${#issues[@]}" "the caller's issue list is left intact"

echo "== require_root =="
reset_state
# require_root ends in `exec sudo`, which would replace this test process, so
# both branches run in a child shell against the fake sudo on PATH. EUID is
# readonly in bash and cannot be assigned, so the non-root branch is reached by
# running as the real (non-root) user and the root branch by shimming EUID
# through a wrapper that sources the lib with EUID already 0 -- which only
# `env -i` style faking can do. Instead: assert the observable behaviour of
# each branch via the fake sudo's call log.
cat >"${TEST_TMPDIR}/root_probe.sh" <<PROBE
#!/usr/bin/env bash
set -euo pipefail
. "${LIB_DIR}/services_common.sh"
require_root "\$@"
printf 'reached-past-require-root\n'
PROBE
chmod +x "${TEST_TMPDIR}/root_probe.sh"

probe_out="$("${TEST_TMPDIR}/root_probe.sh" --status 2>&1 || true)"
if [[ $EUID -ne 0 ]]; then
	_t_called_in "$probe_out" "requires root privileges" "a non-root run announces the re-exec"
	_t_called 'sudo -E bash .*root_probe.sh --status' "it re-execs itself under sudo with its args"
else
	_t_called_in "$probe_out" "reached-past-require-root" "a root run proceeds without re-execing"
	_t_not_called 'sudo -E bash' "a root run does not re-exec"
fi

echo "== hosts_pacman_hooks_installed =="
reset_state
# The two hook paths are absolute and root-owned, so this asserts the real
# machine's answer rather than a fixture: whichever way it goes, the function
# must agree with the filesystem it is reading.
if [[ -f /etc/pacman.d/hooks/10-guard-lib-unlock-all.hook &&
	-f /etc/pacman.d/hooks/90-guard-lib-relock-all.hook ]]; then
	if hosts_pacman_hooks_installed; then
		_t_pass "reports the guard-lib hook pair as installed when both exist"
	else
		_t_fail "reports the guard-lib hook pair as installed when both exist"
	fi
else
	if hosts_pacman_hooks_installed; then
		_t_fail "reports the hook pair as absent when either is missing"
	else
		_t_pass "reports the hook pair as absent when either is missing"
	fi
fi

_t_summary

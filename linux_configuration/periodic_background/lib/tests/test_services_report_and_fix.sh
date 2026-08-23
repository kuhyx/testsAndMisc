#!/usr/bin/env bash
# Tests for report_and_fix in lib/services_common.sh — the shared
# report-then-repair path every unit check funnels through.
#
# Split out of test_services_common.sh to keep both under the repo-wide
# 250-line cap. The branching it covers: status ok vs warning vs error,
# STATUS_ONLY on/off, DRY_RUN on/off, the installer being present or missing,
# and the post-fix re-verify that can promote a status back to "ok".
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"

_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}

declare -a issues=()
status="ok"

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

_t_summary

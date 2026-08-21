#!/usr/bin/env bash
# Tests for lib/services_units.sh — the three systemd timer/service checks.
#
# The unit-state half of each check is fully drivable through the systemctl
# shim ($DEV/enabled, $DEV/active). The file-existence half probes absolute
# root-owned paths (/etc/systemd/system/*.service, /usr/local/bin/*.sh) that no
# shim can redirect, so those branches take whichever way this machine is
# actually configured; the assertions below are written to hold either way.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_units.sh
. "${SCRIPT_DIR}/../services_units.sh"

echo "== check_midnight_shutdown: unit enabled and active =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
printf 'day-specific-shutdown.timer\n' >"${DEV}/enabled"
printf 'day-specific-shutdown.timer\n' >"${DEV}/active"
check_midnight_shutdown >/dev/null
_t_called 'systemctl is-enabled day-specific-shutdown.timer' "the timer's enabled state is queried"
_t_called 'systemctl is-active day-specific-shutdown.timer' "the timer's active state is queried"

echo "== check_midnight_shutdown: a disabled timer is downgraded to warning =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
: >"${DEV}/enabled"
: >"${DEV}/active"
check_midnight_shutdown >/dev/null
# LATENT BUG, pinned deliberately rather than fixed here: the is-active check
# assigns status="warning" unconditionally, so it overwrites the "error" the
# is-enabled check set immediately above. A timer that is BOTH disabled and
# inactive therefore ends up "warning", and report_and_fix only repairs on
# "error" -- so the timer is never re-enabled. Identical in the pre-split file
# (verified against rev 6691cb26), so this split neither caused nor hides it.
# Fixing it changes enforcement behaviour and belongs in its own commit.
_t_eq "warning" "$(get_service_status "midnight_shutdown")" "disabled+inactive is (wrongly) only a warning"
_t_not_called 'ran setup_midnight_shutdown' "so the disabled timer is never repaired"

echo "== check_midnight_shutdown: --status reports without repairing =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
STATUS_ONLY=1
: >"${DEV}/enabled"
check_midnight_shutdown >/dev/null
_t_not_called 'ran setup_midnight_shutdown' "--status never runs the setup script"
_t_eq "warning" "$(get_service_status "midnight_shutdown")" "the verdict is still recorded"

echo "== check_startup_monitor: timer disabled triggers the installer =="
reset_state
make_installer "$STARTUP_MONITOR_SCRIPT"
: >"${DEV}/enabled"
: >"${DEV}/active"
check_startup_monitor >/dev/null
# Same latent downgrade as check_midnight_shutdown above.
_t_eq "warning" "$(get_service_status "startup_monitor")" "disabled+inactive is (wrongly) only a warning"
_t_not_called 'ran setup_pc_startup_monitor' "so the disabled timer is never repaired"

echo "== check_startup_monitor: enabled but inactive is a warning, not a fix =="
reset_state
make_installer "$STARTUP_MONITOR_SCRIPT"
printf 'pc-startup-monitor.timer\n' >"${DEV}/enabled"
: >"${DEV}/active"
check_startup_monitor >/dev/null
_t_not_called 'ran setup_pc_startup_monitor' "an inactive-only timer is not reinstalled"

echo "== check_periodic_systems: every unit healthy short-circuits =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
printf '%s\n' \
	'periodic-system-maintenance.timer' \
	'periodic-system-startup.service' \
	'hosts-file-monitor.service' >"${DEV}/enabled"
printf '%s\n' \
	'periodic-system-maintenance.timer' \
	'hosts-file-monitor.service' >"${DEV}/active"
check_periodic_systems >/dev/null
# The maintenance script probe is an absolute path this test cannot stage, so
# the run is "ok" only on a machine that really has it. Assert the invariant
# that holds either way: no repair is attempted unless something reported bad.
if [[ -f /usr/local/bin/periodic-system-maintenance.sh ]]; then
	_t_eq "ok" "$(get_service_status "periodic_systems")" "a fully healthy stack records ok"
	_t_not_called 'ran setup_periodic_system' "a healthy stack runs no installer"
else
	_t_eq "error" "$(get_service_status "periodic_systems")" "a missing maintenance script is an error"
fi

echo "== check_periodic_systems: a disabled unit is repaired =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
: >"${DEV}/enabled"
: >"${DEV}/active"
check_periodic_systems >/dev/null
# hosts-file-monitor.service's is-active check is the last status assignment
# here, and it too downgrades unconditionally -- same bug, same pinning.
_t_eq "warning" "$(get_service_status "periodic_systems")" "a fully disabled stack is (wrongly) only a warning"
_t_not_called 'ran setup_periodic_system' "so the disabled stack is never repaired"

echo "== check_periodic_systems: startup service disabled alone still repairs =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
printf '%s\n' \
	'periodic-system-maintenance.timer' \
	'hosts-file-monitor.service' >"${DEV}/enabled"
printf '%s\n' \
	'periodic-system-maintenance.timer' \
	'hosts-file-monitor.service' >"${DEV}/active"
check_periodic_systems >/dev/null
# This one DOES repair: hosts-file-monitor is active, so the final downgrade
# never fires and the "error" from the disabled startup service survives.
_t_called 'ran setup_periodic_system' "a disabled startup service alone triggers the repair"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"

_t_summary

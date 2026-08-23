#!/usr/bin/env bash
# Tests for lib/services_units.sh — the three systemd timer/service checks.
#
# Unit state comes from the systemctl shim ($DEV/enabled, $DEV/active); the
# service files and manager scripts are real files under $SYSROOT, staged with
# sysfile. Both halves of every branch are therefore reachable without touching
# the machine this runs on.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_units.sh
. "${SCRIPT_DIR}/../services_units.sh"

# Stage the on-disk half of a healthy midnight-shutdown install.
stage_midnight_files() {
	sysfile etc/systemd/system/day-specific-shutdown.service
	sysfile usr/local/bin/day-specific-shutdown-manager.sh
}

echo "== check_midnight_shutdown: fully healthy records ok =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
stage_midnight_files
printf 'day-specific-shutdown.timer\n' >"${DEV}/enabled"
printf 'day-specific-shutdown.timer\n' >"${DEV}/active"
check_midnight_shutdown >/dev/null
_t_called 'systemctl is-enabled day-specific-shutdown.timer' "the timer's enabled state is queried"
_t_called 'systemctl is-active day-specific-shutdown.timer' "the timer's active state is queried"
_t_eq "ok" "$(get_service_status "midnight_shutdown")" "a fully healthy install records ok"
_t_not_called 'ran setup_midnight_shutdown' "a healthy install runs no setup script"

echo "== check_midnight_shutdown: a missing service file is an error and is repaired =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
sysfile usr/local/bin/day-specific-shutdown-manager.sh
printf 'day-specific-shutdown.timer\n' >"${DEV}/enabled"
printf 'day-specific-shutdown.timer\n' >"${DEV}/active"
check_midnight_shutdown >/dev/null
_t_called 'ran setup_midnight_shutdown.sh enable' "a missing unit file runs the setup script with 'enable'"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"

echo "== check_midnight_shutdown: a missing manager script is an error =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
sysfile etc/systemd/system/day-specific-shutdown.service
printf 'day-specific-shutdown.timer\n' >"${DEV}/enabled"
printf 'day-specific-shutdown.timer\n' >"${DEV}/active"
check_midnight_shutdown >/dev/null
_t_called 'ran setup_midnight_shutdown' "a missing manager script runs the setup script"

echo "== check_midnight_shutdown: a disabled timer is downgraded to warning =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
stage_midnight_files
: >"${DEV}/enabled"
: >"${DEV}/active"
check_midnight_shutdown >/dev/null
# Regression test. The is-active check used to assign status="warning"
# unconditionally, overwriting the "error" the is-enabled check set just above;
# since report_and_fix only repairs on "error", a timer that was BOTH disabled
# and inactive -- the normal shape of a genuinely broken timer -- was reported
# and then never re-enabled.
_t_eq "error" "$(get_service_status "midnight_shutdown")" "disabled+inactive stays an error"
_t_called 'ran setup_midnight_shutdown.sh enable' "so the disabled timer IS repaired"

echo "== check_midnight_shutdown: --status reports without repairing =="
reset_state
make_installer "$MIDNIGHT_SHUTDOWN_SCRIPT"
stage_midnight_files
STATUS_ONLY=1
: >"${DEV}/enabled"
check_midnight_shutdown >/dev/null
_t_not_called 'ran setup_midnight_shutdown' "--status never runs the setup script"
_t_eq "error" "$(get_service_status "midnight_shutdown")" "the error is still recorded"

echo "== check_startup_monitor: fully healthy records ok =="
reset_state
make_installer "$STARTUP_MONITOR_SCRIPT"
sysfile etc/systemd/system/pc-startup-monitor.service
sysfile usr/local/bin/pc-startup-check.sh
printf 'pc-startup-monitor.timer\n' >"${DEV}/enabled"
printf 'pc-startup-monitor.timer\n' >"${DEV}/active"
check_startup_monitor >/dev/null
_t_eq "ok" "$(get_service_status "startup_monitor")" "a fully healthy install records ok"

echo "== check_startup_monitor: missing files are errors and are repaired =="
reset_state
make_installer "$STARTUP_MONITOR_SCRIPT"
printf 'pc-startup-monitor.timer\n' >"${DEV}/enabled"
printf 'pc-startup-monitor.timer\n' >"${DEV}/active"
check_startup_monitor >/dev/null
_t_called 'ran setup_pc_startup_monitor' "missing files run the setup script"

echo "== check_startup_monitor: timer disabled is downgraded to warning =="
reset_state
make_installer "$STARTUP_MONITOR_SCRIPT"
sysfile etc/systemd/system/pc-startup-monitor.service
sysfile usr/local/bin/pc-startup-check.sh
: >"${DEV}/enabled"
: >"${DEV}/active"
check_startup_monitor >/dev/null
# Same regression as check_midnight_shutdown above.
_t_eq "error" "$(get_service_status "startup_monitor")" "disabled+inactive stays an error"
_t_called 'ran setup_pc_startup_monitor' "so the disabled timer IS repaired"

echo "== check_startup_monitor: enabled but inactive is a warning, not a fix =="
reset_state
make_installer "$STARTUP_MONITOR_SCRIPT"
sysfile etc/systemd/system/pc-startup-monitor.service
sysfile usr/local/bin/pc-startup-check.sh
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
sysfile usr/local/bin/periodic-system-maintenance.sh
check_periodic_systems >/dev/null
_t_eq "ok" "$(get_service_status "periodic_systems")" "a fully healthy stack records ok"
_t_not_called 'ran setup_periodic_system' "a healthy stack runs no installer"

echo "== check_periodic_systems: a missing maintenance script is repaired =="
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
_t_called 'ran setup_periodic_system' "a missing maintenance script runs the setup script"

echo "== check_periodic_systems: a disabled unit is repaired =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
sysfile usr/local/bin/periodic-system-maintenance.sh
: >"${DEV}/enabled"
: >"${DEV}/active"
check_periodic_systems >/dev/null
# hosts-file-monitor.service's is-active check is the LAST status assignment in
# this function, so before the fix it downgraded everything above it.
_t_eq "error" "$(get_service_status "periodic_systems")" "a fully disabled stack stays an error"
_t_called 'ran setup_periodic_system' "so the disabled stack IS repaired"

echo "== check_periodic_systems: startup service disabled alone still repairs =="
reset_state
make_installer "$PERIODIC_SYSTEM_SCRIPT"
printf '%s\n' \
	'periodic-system-maintenance.timer' \
	'hosts-file-monitor.service' >"${DEV}/enabled"
printf '%s\n' \
	'periodic-system-maintenance.timer' \
	'hosts-file-monitor.service' >"${DEV}/active"
sysfile usr/local/bin/periodic-system-maintenance.sh
check_periodic_systems >/dev/null
# This one DOES repair: hosts-file-monitor is active, so the final downgrade
# never fires and the "error" from the disabled startup service survives.
_t_called 'ran setup_periodic_system' "a disabled startup service alone triggers the repair"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"

_t_summary

#!/usr/bin/env bash
# lib/services_units.sh — systemd timer/service checks for the three units that
# are installed by their own setup scripts (midnight shutdown, PC startup
# monitor, periodic maintenance).
#
# Sourced by check_and_enable_services.sh. All three funnel their findings
# through report_and_fix, which owns the reinstall-and-reverify path.

# Absolute paths the checks below probe are prefixed with $SYSROOT, which is
# empty in production and a fixture tree under test. It is deliberately NOT
# defaulted here: several repairs in this family write outside `run` (chattr,
# find -delete, an append to resolved.conf), so a test that forgot to set it
# would edit the real /etc. Unset is a hard error; empty is the real filesystem.
SYSROOT="${SERVICES_ROOT?SERVICES_ROOT must be set (empty = the real filesystem)}"

check_midnight_shutdown() {
	header "Midnight Shutdown (Day-Specific Auto-Shutdown)"

	local status="ok"
	local issues=()

	# Check timer
	if systemctl is-enabled day-specific-shutdown.timer &>/dev/null; then
		msg "day-specific-shutdown.timer is enabled"
	else
		issues+=("day-specific-shutdown.timer is not enabled")
		status="error"
	fi

	if systemctl is-active day-specific-shutdown.timer &>/dev/null; then
		msg "day-specific-shutdown.timer is active"
	else
		issues+=("day-specific-shutdown.timer is not active")
		status="warning"
	fi

	# Check service file exists
	if [[ -f "${SYSROOT}/etc/systemd/system/day-specific-shutdown.service" ]]; then
		msg "day-specific-shutdown.service file exists"
	else
		issues+=("day-specific-shutdown.service file missing")
		status="error"
	fi

	# Check management script
	if [[ -f "${SYSROOT}/usr/local/bin/day-specific-shutdown-manager.sh" ]]; then
		msg "Shutdown manager script exists"
	else
		issues+=("day-specific-shutdown-manager.sh not found")
		status="error"
	fi

	report_and_fix issues status "midnight_shutdown" \
		"Setting up midnight shutdown..." \
		"$MIDNIGHT_SHUTDOWN_SCRIPT" \
		"day-specific-shutdown.timer" \
		enable
}

check_startup_monitor() {
	header "PC Startup Monitor"

	local status="ok"
	local issues=()

	# Check timer (the timer triggers the service, so we check the timer)
	if systemctl is-enabled pc-startup-monitor.timer &>/dev/null; then
		msg "pc-startup-monitor.timer is enabled"
	else
		issues+=("pc-startup-monitor.timer is not enabled")
		status="error"
	fi

	if systemctl is-active pc-startup-monitor.timer &>/dev/null; then
		msg "pc-startup-monitor.timer is active"
	else
		issues+=("pc-startup-monitor.timer is not active")
		status="warning"
	fi

	# Check service file exists
	if [[ -f "${SYSROOT}/etc/systemd/system/pc-startup-monitor.service" ]]; then
		msg "pc-startup-monitor.service file exists"
	else
		issues+=("pc-startup-monitor.service file missing")
		status="error"
	fi

	# Check monitor script
	if [[ -f "${SYSROOT}/usr/local/bin/pc-startup-check.sh" ]]; then
		msg "Startup check script exists"
	else
		issues+=("pc-startup-check.sh not found")
		status="error"
	fi

	report_and_fix issues status "startup_monitor" \
		"Setting up startup monitor..." \
		"$STARTUP_MONITOR_SCRIPT" \
		"pc-startup-monitor.timer"
}

check_periodic_systems() {
	header "Periodic System Maintenance"

	local status="ok"
	local issues=()

	# Check timer
	if systemctl is-enabled periodic-system-maintenance.timer &>/dev/null; then
		msg "periodic-system-maintenance.timer is enabled"
	else
		issues+=("periodic-system-maintenance.timer is not enabled")
		status="error"
	fi

	if systemctl is-active periodic-system-maintenance.timer &>/dev/null; then
		msg "periodic-system-maintenance.timer is active"
	else
		issues+=("periodic-system-maintenance.timer is not active")
		status="warning"
	fi

	# Check startup service
	if systemctl is-enabled periodic-system-startup.service &>/dev/null; then
		msg "periodic-system-startup.service is enabled"
	else
		issues+=("periodic-system-startup.service is not enabled")
		status="error"
	fi

	# Check hosts file monitor
	if systemctl is-enabled hosts-file-monitor.service &>/dev/null; then
		msg "hosts-file-monitor.service is enabled"
	else
		issues+=("hosts-file-monitor.service is not enabled")
		status="error"
	fi

	if systemctl is-active hosts-file-monitor.service &>/dev/null; then
		msg "hosts-file-monitor.service is active"
	else
		issues+=("hosts-file-monitor.service is not active")
		status="warning"
	fi

	# Check maintenance script
	if [[ -f "${SYSROOT}/usr/local/bin/periodic-system-maintenance.sh" ]]; then
		msg "Maintenance script exists"
	else
		issues+=("periodic-system-maintenance.sh not found")
		status="error"
	fi

	# report_and_fix takes `status` by nameref and both reads and rewrites it,
	# so passing the bare name is the whole interface. shellcheck cannot see
	# through a nameref, though, and standalone it reports the assignments
	# above as write-only (SC2034). This early return is a genuine read: an
	# "ok" service has nothing to report and nothing to fix, so skipping the
	# call is also marginally cheaper than having it decide the same thing.
	if [[ $status == "ok" ]]; then
		set_service_status "periodic_systems" "ok"
		return 0
	fi
	report_and_fix issues status "periodic_systems" \
		"Setting up periodic systems..." \
		"$PERIODIC_SYSTEM_SCRIPT" \
		"periodic-system-maintenance.timer"
}

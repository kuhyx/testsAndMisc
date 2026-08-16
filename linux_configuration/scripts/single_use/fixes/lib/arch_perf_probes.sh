#!/bin/bash
# Individual diagnostic probes for the Arch performance report.
#
# Sourced by diagnose_arch_performance.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

collect_basics() {
	run_and_log "Kernel" uname -a
	run_and_log "Uptime" uptime
	run_and_log "Memory" free -h
	run_and_log "Swap" swapon --show
	run_and_log "CPU (lscpu)" lscpu
	run_and_log "Disk Usage" df -h /
	run_and_log "Boot Time" systemd-analyze
	run_and_log "Failed Units" systemctl --failed --no-pager
	run_and_log "Recent Errors (this boot)" journalctl -b -p err --no-pager -n 200

	local cpu_count
	cpu_count=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
	local load1
	load1=$(awk '{print int($1)}' /proc/loadavg 2>/dev/null || echo 0)
	if [[ ${load1:-0} -ge ${cpu_count:-1} ]]; then
		add_finding "1-minute load average is at/above CPU thread count (${load1}/${cpu_count}); background tasks may be saturating the system."
	fi

	local failed_count
	failed_count=$(systemctl --failed --no-legend 2>/dev/null | wc -l || true)
	failed_count=${failed_count//[[:space:]]/}
	if [[ ${failed_count:-0} -gt 0 ]]; then
		add_finding "One or more systemd units are failed (${failed_count}); failed services can cause repeated retries and instability."
	fi

	local acpi_error_count
	acpi_error_count=$(journalctl -b -p err --no-pager 2>/dev/null | grep -ic 'acpi' || true)
	if [[ ${acpi_error_count:-0} -ge 5 ]]; then
		add_finding "Frequent ACPI errors detected in current boot (${acpi_error_count}); BIOS/firmware update may improve stability."
	fi

	local top_snapshot
	top_snapshot=$(ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 12 || true)
	{
		echo
		echo "=== Top CPU Processes ==="
		echo "$top_snapshot"
	} >>"$REPORT_FILE"

	local xorg_cpu
	xorg_cpu=$(ps -C Xorg -o %cpu= | awk '{sum+=$1} END {printf "%.0f", sum+0}' || echo 0)
	if [[ ${xorg_cpu:-0} -ge 20 ]]; then
		add_finding "Xorg is using high CPU (${xorg_cpu}%); desktop/compositor/GPU driver path may be a primary slowdown source."
	fi
}

check_cpu_governor() {
	# An ARRAY, not a newline-joined string: the awk/grep calls below need one
	# argument per file. With the old unquoted "$gov_files" an empty result
	# also left awk with NO file operands, so it fell through to reading stdin
	# and the diagnostic hung instead of reporting 'not found'.
	local -a gov_files=()
	mapfile -t gov_files < <(find /sys/devices/system/cpu -maxdepth 3 -name scaling_governor 2>/dev/null || true)

	if ((${#gov_files[@]} == 0)); then
		add_action "CPU governor files not found (may be unsupported on this platform)."
		return
	fi

	local summary
	summary=$(awk '{count[$1]++} END {for (g in count) printf "%s:%d ", g, count[g]}' "${gov_files[@]}" 2>/dev/null || true)
	echo "CPU governor summary: ${summary:-unknown}" >>"$REPORT_FILE"

	if grep -q '^powersave$' "${gov_files[@]}" 2>/dev/null; then
		add_finding "CPU governor includes 'powersave' on one or more cores; this can make high-end hardware feel slow."
	fi
}

check_thermal_state() {
	if has_cmd sensors; then
		run_and_log "Temperatures (sensors)" sensors
	else
		add_action "Install lm_sensors and run 'sensors' to verify thermal throttling."
	fi

	if has_cmd dmesg; then
		local therm_hits
		therm_hits=$(dmesg | grep -Ei 'throttl|thermal|overheat|cpu clock throttled' | tail -n 30 || true)
		if [[ -n $therm_hits ]]; then
			add_finding "Kernel logs show thermal/throttling related messages."
			{
				echo
				echo "=== Thermal/Throttling dmesg excerpts ==="
				echo "$therm_hits"
			} >>"$REPORT_FILE"
		fi
	fi
}

check_power_services() {
	local tlp_enabled="false"
	local ppd_enabled="false"

	if systemctl is-enabled tlp.service >/dev/null 2>&1; then
		tlp_enabled="true"
	fi
	if systemctl is-enabled power-profiles-daemon.service >/dev/null 2>&1; then
		ppd_enabled="true"
	fi

	echo "Power services: tlp=${tlp_enabled}, power-profiles-daemon=${ppd_enabled}" >>"$REPORT_FILE"

	if [[ $tlp_enabled == "true" && $ppd_enabled == "true" ]]; then
		add_finding "Both TLP and power-profiles-daemon are enabled; they often conflict and cause inconsistent performance."
	fi

	if [[ $tlp_enabled == "false" && $ppd_enabled == "false" ]]; then
		add_action "No power management daemon is enabled; consider installing/enabling power-profiles-daemon for predictable AC/battery behavior."
	fi
}

check_storage_health() {
	run_and_log "Block Devices" lsblk -o NAME,MODEL,ROTA,SIZE,TYPE,MOUNTPOINT,FSTYPE

	if has_cmd fstrim; then
		run_and_log "fstrim dry-run" fstrim -av --dry-run
	fi

	if systemctl is-enabled fstrim.timer >/dev/null 2>&1; then
		add_action "fstrim.timer is enabled (good for SSD performance longevity)."
	else
		add_finding "fstrim.timer is not enabled; SSD maintenance trimming may be missing."
	fi

	if has_cmd smartctl; then
		local root_disk
		root_disk=$(findmnt -n -o SOURCE / | sed 's/[0-9]*$//' | sed 's/p$//' || true)
		if [[ -n ${root_disk:-} && -b $root_disk ]]; then
			run_and_log "SMART Summary ($root_disk)" smartctl -H "$root_disk"
		fi
	else
		add_action "Install smartmontools and run SMART health checks for your SSD/NVMe."
	fi
}

check_memory_pressure() {
	local mem_total mem_available swap_total swap_free
	mem_total=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
	mem_available=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
	swap_total=$(awk '/SwapTotal/ {print $2}' /proc/meminfo)
	swap_free=$(awk '/SwapFree/ {print $2}' /proc/meminfo)

	if [[ ${swap_total:-0} -gt 0 ]]; then
		local swap_used
		swap_used=$((swap_total - swap_free))
		local swap_pct
		swap_pct=$((swap_used * 100 / swap_total))
		echo "Swap usage: ${swap_pct}%" >>"$REPORT_FILE"
		if [[ $swap_pct -ge 35 && ${mem_available:-0} -gt $((mem_total / 3)) ]]; then
			add_finding "High swap usage while RAM is still available; this can cause stutter."
			add_action "Consider lowering swappiness (temporary: sudo sysctl vm.swappiness=10)."
		fi
	fi

	if [[ -f /proc/pressure/memory ]]; then
		run_and_log "Memory PSI" cat /proc/pressure/memory
	fi
}

#!/bin/bash
# CPU governor and IO scheduler tweaks.
#
# Sourced by optimize_arch_desktop.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

# ===================================================================
# 1. CPU Governor → performance
# ===================================================================
tweak_cpu_governor() {
	local gov_files
	gov_files=$(find /sys/devices/system/cpu -maxdepth 3 -name scaling_governor 2>/dev/null || true)

	if [[ -z $gov_files ]]; then
		log_warn "No CPU governor sysfs files found — skipping."
		return 0
	fi

	# Check current state
	local all_performance=true
	local f
	for f in $gov_files; do
		if [[ $(cat "$f") != "performance" ]]; then
			all_performance=false
			break
		fi
	done

	if [[ $all_performance == "true" ]]; then
		log_ok "All CPU cores already on 'performance' governor — skipping."
		return 0
	fi

	for f in $gov_files; do
		echo "performance" >"$f"
	done

	# Make it persistent via a sysctl-style drop-in using udev rule
	local udev_rule="/etc/udev/rules.d/60-cpu-governor-performance.rules"
	if [[ ! -f $udev_rule ]]; then
		cat >"$udev_rule" <<'UDEVEOF'
# Set CPU governor to performance on all cores at boot
SUBSYSTEM=="module", DEVPATH=="*/cpu/*", ATTR{scaling_governor}=="*", ATTR{scaling_governor}="performance"
UDEVEOF
	fi

	# Also install cpupower hook as a more reliable persistence method
	local cpupower_conf="/etc/default/cpupower"
	if has_cmd cpupower; then
		if [[ ! -f $cpupower_conf ]] || ! grep -q "^governor='performance'" "$cpupower_conf" 2>/dev/null; then
			mkdir -p "$(dirname "$cpupower_conf")"
			cat >"$cpupower_conf" <<'CPUEOF'
# /etc/default/cpupower — managed by optimize_arch_desktop.sh
governor='performance'
CPUEOF
			systemctl enable cpupower.service 2>/dev/null || true
		fi
	fi

	return 0
}

# ===================================================================
# 2. I/O Scheduler per drive type
# ===================================================================
tweak_io_scheduler() {
	local changed=false

	local block_dev
	for block_dev in /sys/block/sd* /sys/block/nvme* /sys/block/vd*; do
		[[ -d $block_dev ]] || continue
		local sched_file="$block_dev/queue/scheduler"
		[[ -f $sched_file ]] || continue

		local dev_name
		dev_name=$(basename "$block_dev")
		local rotational
		rotational=$(cat "$block_dev/queue/rotational" 2>/dev/null || echo 1)
		local current
		current=$(sed 's/.*\[\(.*\)\].*/\1/' "$sched_file" 2>/dev/null || true)

		local target
		if [[ $dev_name == nvme* ]]; then
			target="none"
		elif [[ $rotational -eq 0 ]]; then
			target="mq-deadline"
		else
			target="bfq"
		fi

		if [[ $current == "$target" ]]; then
			log_ok "$dev_name: already using '$target' scheduler."
			continue
		fi

		echo "$target" >"$sched_file" 2>/dev/null || true
		log_info "$dev_name: scheduler changed from '$current' to '$target'."
		changed=true
	done

	# Persist via udev rule
	local udev_rule="/etc/udev/rules.d/60-io-scheduler.rules"
	if [[ ! -f $udev_rule ]]; then
		cat >"$udev_rule" <<'IOEOF'
# NVMe: no scheduler (multi-queue hardware handles it)
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"
# SATA SSD: mq-deadline (low latency)
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="mq-deadline"
# HDD: BFQ (fair bandwidth allocation)
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="1", ATTR{queue/scheduler}="bfq"
IOEOF
	fi

	if [[ $changed == "false" ]]; then
		log_ok "All I/O schedulers already optimal."
	fi

	return 0
}

# ===================================================================
# Apply all tweaks
# ===================================================================

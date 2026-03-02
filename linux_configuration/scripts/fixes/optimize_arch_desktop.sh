#!/usr/bin/env bash

# Optimize Arch Linux desktop for maximum performance on high-end hardware
#
# Tuning areas:
#  1. CPU scheduler — performance governor on all cores
#  2. I/O scheduler — optimal scheduler per drive type (none for NVMe, mq-deadline for SATA SSD)
#  3. Memory / swap — lower swappiness, tune dirty page writeback for responsiveness
#  4. Kernel network — TCP BBR, fastopen, larger buffers
#  5. Filesystem — fstrim timer, noatime advisory
#  6. NVIDIA GPU — max performance level via persistence mode
#  7. Kernel mitigations — option to disable CPU vulnerability mitigations for extra speed
#  8. Boot speed — disable unnecessary wait-online services
#  9. Journal housekeeping — cap at 300M
# 10. Process scheduler — install ananicy-cpp for automatic nice/ionice/scheduling
#
# Usage:
#   ./optimize_arch_desktop.sh                  # Apply safe optimizations
#   ./optimize_arch_desktop.sh --dry-run        # Show what would be done
#   ./optimize_arch_desktop.sh --interactive    # Prompt before each tweak
#   ./optimize_arch_desktop.sh --aggressive     # Include CPU mitigation disable (risk: security)
#   ./optimize_arch_desktop.sh -h               # Show help
#
# All tweaks are idempotent and safe to re-run.
# Some kernel parameter changes require a reboot to take full effect.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

DRY_RUN=false
AGGRESSIVE=false

for arg in "$@"; do
	case "$arg" in
	--dry-run)
		DRY_RUN=true
		;;
	--aggressive)
		AGGRESSIVE=true
		;;
	-h | --help)
		cat <<'EOF'
optimize_arch_desktop.sh - Squeeze maximum performance from an Arch Linux desktop

Usage: optimize_arch_desktop.sh [OPTIONS]

Options:
  --dry-run          Show what would be done without making changes
  --aggressive       Also disable CPU vulnerability mitigations (trades security for speed)
  -i, --interactive  Prompt before each optimization
  -h, --help         Show this help message

Optimizations applied:
   1. Set CPU governor to performance on all cores
   2. Set optimal I/O scheduler per drive (none/mq-deadline)
   3. Tune vm.swappiness, dirty ratios, vfs_cache_pressure via sysctl
   4. Enable TCP BBR congestion control + fastopen + buffer tuning
   5. Enable fstrim.timer for SSD TRIM maintenance
   6. Set NVIDIA GPU to max performance level (persistence mode)
   7. [--aggressive] Disable CPU vulnerability mitigations
   8. Disable NetworkManager-wait-online.service for faster boot
   9. Vacuum & cap systemd journal at 300M
  10. Install/enable ananicy-cpp for automatic process prioritization

All optimizations are idempotent. Re-run safely at any time.
EOF
		exit 0
		;;
	esac
done

require_root "$@"

print_setup_header "Arch Linux Desktop Performance Optimizer"

TWEAKS_APPLIED=0
TWEAKS_SKIPPED=0

# ---------------------------------------------------------------------------
# Helper: apply or preview a tweak
# ---------------------------------------------------------------------------
apply_tweak() {
	local description="$1"
	shift

	echo ""
	log_info "$description"

	if [[ $DRY_RUN == "true" ]]; then
		echo "  [dry-run] Would run: $*"
		return 0
	fi

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		if ! ask_yes_no "  Apply this optimization?"; then
			log_warn "Skipped."
			((TWEAKS_SKIPPED++)) || true
			return 0
		fi
	fi

	if "$@"; then
		log_ok "Done."
		((TWEAKS_APPLIED++)) || true
	else
		log_error "Failed (non-fatal, continuing)."
	fi
}

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
# 3. Memory & swap tuning via sysctl
# ===================================================================
tweak_vm_sysctl() {
	local dropin="/etc/sysctl.d/90-desktop-performance.conf"

	# Desktop workloads: low swappiness, aggressive VFS caching, tuned dirty ratios
	local -A params=(
		["vm.swappiness"]="10"
		["vm.vfs_cache_pressure"]="50"
		["vm.dirty_ratio"]="15"
		["vm.dirty_background_ratio"]="5"
		["vm.dirty_writeback_centisecs"]="1500"
		["vm.page-cluster"]="0"
	)

	local needs_update=false
	local key
	for key in "${!params[@]}"; do
		local current
		current=$(sysctl -n "$key" 2>/dev/null || true)
		if [[ $current != "${params[$key]}" ]]; then
			needs_update=true
			break
		fi
	done

	if [[ $needs_update == "false" && -f $dropin ]]; then
		log_ok "VM sysctl parameters already tuned — skipping."
		return 0
	fi

	cat >"$dropin" <<'VMEOF'
# Desktop performance tuning — managed by optimize_arch_desktop.sh
#
# vm.swappiness=10          — prefer keeping data in RAM over swapping
# vm.vfs_cache_pressure=50  — favor keeping inode/dentry caches (speeds up file operations)
# vm.dirty_ratio=15         — allow up to 15% RAM dirty before synchronous writeback
# vm.dirty_background_ratio=5  — start async writeback at 5% dirty
# vm.dirty_writeback_centisecs=1500  — flush dirty pages every 15s (less I/O churn)
# vm.page-cluster=0         — read one page at a time from swap (reduces latency on SSD)
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.dirty_writeback_centisecs = 1500
vm.page-cluster = 0
VMEOF

	sysctl --system >/dev/null 2>&1
	return 0
}

# ===================================================================
# 4. Network: TCP BBR + fastopen + buffer tuning
# ===================================================================
tweak_network_sysctl() {
	local dropin="/etc/sysctl.d/91-desktop-network.conf"

	# Check if BBR module is available
	if ! modprobe tcp_bbr 2>/dev/null; then
		log_warn "tcp_bbr kernel module unavailable — skipping network tuning."
		return 0
	fi

	local -A params=(
		["net.core.default_qdisc"]="fq"
		["net.ipv4.tcp_congestion_control"]="bbr"
		["net.ipv4.tcp_fastopen"]="3"
		["net.core.rmem_max"]="16777216"
		["net.core.wmem_max"]="16777216"
		["net.ipv4.tcp_rmem"]="4096 1048576 16777216"
		["net.ipv4.tcp_wmem"]="4096 1048576 16777216"
		["net.ipv4.tcp_mtu_probing"]="1"
	)

	local needs_update=false
	local key
	for key in "${!params[@]}"; do
		local current
		current=$(sysctl -n "$key" 2>/dev/null || true)
		# Normalize whitespace for comparison (kernel uses tabs)
		current=$(echo "$current" | xargs)
		local expected
		expected=$(echo "${params[$key]}" | xargs)
		if [[ $current != "$expected" ]]; then
			needs_update=true
			break
		fi
	done

	if [[ $needs_update == "false" && -f $dropin ]]; then
		log_ok "Network sysctl parameters already tuned — skipping."
		return 0
	fi

	cat >"$dropin" <<'NETEOF'
# Network performance tuning — managed by optimize_arch_desktop.sh
#
# BBR congestion control — better throughput and lower latency than cubic
# TCP fastopen — saves one RTT on repeated connections (both client and server)
# Larger buffers — helps on high-bandwidth or high-latency links
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216
net.ipv4.tcp_mtu_probing = 1
NETEOF

	sysctl --system >/dev/null 2>&1
	return 0
}

# ===================================================================
# 5. fstrim timer
# ===================================================================
tweak_fstrim() {
	if systemctl is-enabled fstrim.timer >/dev/null 2>&1; then
		log_ok "fstrim.timer already enabled — skipping."
		return 0
	fi

	systemctl enable --now fstrim.timer
	return 0
}

# ===================================================================
# 6. NVIDIA GPU — max performance
# ===================================================================
tweak_nvidia_gpu() {
	if ! has_cmd nvidia-smi; then
		log_info "nvidia-smi not found — skipping GPU tuning."
		return 0
	fi

	# Enable persistence mode (keeps driver loaded, faster app launches)
	local persist_status
	persist_status=$(nvidia-smi --query-gpu=persistence_mode --format=csv,noheader 2>/dev/null | head -n 1 | xargs || true)
	if [[ $persist_status != "Enabled" ]]; then
		nvidia-smi -pm 1 >/dev/null 2>&1 || true
		log_info "NVIDIA persistence mode enabled."
	else
		log_ok "NVIDIA persistence mode already enabled."
	fi

	# Set power management to prefer maximum performance
	# PowerMizerMode: 1 = prefer max perf
	nvidia-smi -gps 0 >/dev/null 2>&1 || true

	# Persist via systemd service
	local service_file="/etc/systemd/system/nvidia-performance.service"
	if [[ ! -f $service_file ]]; then
		cat >"$service_file" <<'NVSVC'
[Unit]
Description=Set NVIDIA GPU to max performance mode
After=nvidia-persistenced.service

[Service]
Type=oneshot
ExecStart=/usr/bin/nvidia-smi -pm 1
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
NVSVC
		systemctl daemon-reload
		systemctl enable nvidia-performance.service 2>/dev/null || true
	fi

	# Ensure nvidia-persistenced is enabled
	if has_cmd nvidia-persistenced; then
		systemctl enable nvidia-persistenced.service 2>/dev/null || true
		if ! systemctl is-active nvidia-persistenced.service >/dev/null 2>&1; then
			systemctl start nvidia-persistenced.service 2>/dev/null || true
		fi
	fi

	return 0
}

# ===================================================================
# 7. [AGGRESSIVE] Disable CPU vulnerability mitigations
# ===================================================================
tweak_mitigations() {
	if [[ $AGGRESSIVE != "true" ]]; then
		log_info "Skipping CPU mitigation disable (use --aggressive to enable)."
		return 0
	fi

	# Detect boot loader
	local boot_method=""
	if [[ -d /boot/loader/entries ]]; then
		boot_method="systemd-boot"
	elif [[ -f /etc/default/grub ]]; then
		boot_method="grub"
	else
		log_warn "Could not detect boot loader — skipping mitigation tweak."
		log_info "Manually add 'mitigations=off' to your kernel command line for extra speed."
		return 0
	fi

	if [[ $boot_method == "systemd-boot" ]]; then
		local entry
		entry=$(find /boot/loader/entries -name '*.conf' -print -quit 2>/dev/null || true)
		if [[ -n $entry ]]; then
			if grep -q 'mitigations=off' "$entry" 2>/dev/null; then
				log_ok "mitigations=off already set in systemd-boot — skipping."
				return 0
			fi
			# Append to the options line
			sed -i '/^options / s/$/ mitigations=off/' "$entry"
			log_warn "Added mitigations=off to $entry. REBOOT REQUIRED."
			log_warn "This trades security for ~5-15% performance. Only for isolated desktops."
		fi
	elif [[ $boot_method == "grub" ]]; then
		if grep -q 'mitigations=off' /etc/default/grub 2>/dev/null; then
			log_ok "mitigations=off already set in GRUB — skipping."
			return 0
		fi
		sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 mitigations=off"/' /etc/default/grub
		grub-mkconfig -o /boot/grub/grub.cfg
		log_warn "Added mitigations=off to GRUB config. REBOOT REQUIRED."
	fi

	return 0
}

# ===================================================================
# 8. Disable NetworkManager-wait-online
# ===================================================================
tweak_nm_wait_online() {
	if ! systemctl is-enabled NetworkManager-wait-online.service >/dev/null 2>&1; then
		log_ok "NetworkManager-wait-online already disabled — skipping."
		return 0
	fi

	systemctl disable NetworkManager-wait-online.service
	return 0
}

# ===================================================================
# 9. Journal vacuum + permanent cap
# ===================================================================
tweak_journal() {
	local usage_line
	usage_line=$(journalctl --disk-usage 2>/dev/null || true)

	local needs_vacuum=false
	if [[ $usage_line =~ ([0-9]+\.?[0-9]*)\ G ]]; then
		needs_vacuum=true
	fi

	if [[ $needs_vacuum == "true" ]]; then
		journalctl --vacuum-size=300M
	else
		log_ok "Journal already under 1GiB."
	fi

	local dropin_dir="/etc/systemd/journald.conf.d"
	local dropin_file="$dropin_dir/size-limit.conf"

	if [[ -f $dropin_file ]] && grep -q 'SystemMaxUse=300M' "$dropin_file"; then
		log_ok "Journal size cap already configured."
	else
		mkdir -p "$dropin_dir"
		cat >"$dropin_file" <<'JOURNALEOF'
[Journal]
SystemMaxUse=300M
JOURNALEOF
		systemctl restart systemd-journald
	fi

	return 0
}

# ===================================================================
# 10. ananicy-cpp — automatic process nice/ionice/scheduler tuning
# ===================================================================
tweak_ananicy() {
	# ananicy-cpp is the C++ rewrite, available in the AUR via ananicy-cpp
	if systemctl is-enabled ananicy-cpp.service >/dev/null 2>&1; then
		log_ok "ananicy-cpp is already enabled — skipping."
		return 0
	fi

	if pacman -Qi ananicy-cpp >/dev/null 2>&1; then
		systemctl enable --now ananicy-cpp.service
		log_info "Enabled ananicy-cpp.service."
		return 0
	fi

	# Check for the original ananicy
	if pacman -Qi ananicy >/dev/null 2>&1; then
		if ! systemctl is-enabled ananicy.service >/dev/null 2>&1; then
			systemctl enable --now ananicy.service
			log_info "Enabled ananicy.service."
		else
			log_ok "ananicy is already enabled."
		fi
		return 0
	fi

	log_info "ananicy-cpp is not installed."
	log_info "Install from AUR for automatic per-process priority tuning:"
	log_info "  yay -S ananicy-cpp cachyos-ananicy-rules-git"

	return 0
}

# ===================================================================
# Apply all tweaks
# ===================================================================
main() {
	apply_tweak \
		"Tweak  1/10: Set CPU governor to performance on all cores" \
		tweak_cpu_governor

	apply_tweak \
		"Tweak  2/10: Optimize I/O scheduler per drive type" \
		tweak_io_scheduler

	apply_tweak \
		"Tweak  3/10: Tune VM/memory sysctl for desktop responsiveness" \
		tweak_vm_sysctl

	apply_tweak \
		"Tweak  4/10: Enable TCP BBR + fastopen + larger buffers" \
		tweak_network_sysctl

	apply_tweak \
		"Tweak  5/10: Enable fstrim.timer for SSD TRIM maintenance" \
		tweak_fstrim

	apply_tweak \
		"Tweak  6/10: NVIDIA GPU persistence mode + max performance" \
		tweak_nvidia_gpu

	apply_tweak \
		"Tweak  7/10: CPU vulnerability mitigations (--aggressive only)" \
		tweak_mitigations

	apply_tweak \
		"Tweak  8/10: Disable NetworkManager-wait-online (faster boot)" \
		tweak_nm_wait_online

	apply_tweak \
		"Tweak  9/10: Vacuum & cap systemd journal at 300M" \
		tweak_journal

	apply_tweak \
		"Tweak 10/10: Enable ananicy-cpp process prioritization" \
		tweak_ananicy

	# ---------------------------------------------------------------
	# Summary
	# ---------------------------------------------------------------
	echo ""
	echo "=============================="
	echo " Desktop Optimization Summary"
	echo "=============================="

	if [[ $DRY_RUN == "true" ]]; then
		log_info "Dry-run mode — no changes were made."
	else
		log_ok "Optimizations applied: $TWEAKS_APPLIED"
		if [[ $TWEAKS_SKIPPED -gt 0 ]]; then
			log_warn "Optimizations skipped: $TWEAKS_SKIPPED"
		fi
	fi

	echo ""

	# Advisory: check for noatime
	local root_mount_opts
	root_mount_opts=$(findmnt -n -o OPTIONS / 2>/dev/null || true)
	if [[ -n $root_mount_opts ]] && ! echo "$root_mount_opts" | grep -q 'noatime'; then
		log_info "Tip: Your root filesystem does not use 'noatime'."
		log_info "  Adding 'noatime' to /etc/fstab can reduce unnecessary disk writes."
		log_info "  (Change 'relatime' or 'atime' to 'noatime' in /etc/fstab, then reboot)"
	fi

	if [[ $AGGRESSIVE == "true" ]]; then
		log_warn "Aggressive mode was used — mitigations=off trades security for speed."
	fi

	echo ""
	log_info "Reboot recommended for kernel parameter and boot loader changes to take effect."
	log_info "Verify after reboot with: diagnose_arch_performance.sh"
}

main

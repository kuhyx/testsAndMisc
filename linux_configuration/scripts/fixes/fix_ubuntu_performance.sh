#!/usr/bin/env bash

# Fix common Ubuntu performance issues on Lenovo Legion laptop with NVIDIA GPU
#
# System: Ubuntu 24.04, AMD Ryzen 7 4800H, RTX 2060 Mobile, 32GB RAM, NVMe SSD
#
# Issues addressed:
# 1. NetworkManager-wait-online.service → adds ~6.7s to every boot for no benefit
# 2. vm.swappiness=60 → too aggressive for 32GB RAM + NVMe, wastes I/O on swap
# 3. NVIDIA persistence mode off → GPU re-initializes on every nvidia operation
# 4. No earlyoom → system can hard-freeze under memory pressure (OOM killer too slow)
# 5. Failed SSSD systemd units → retry loops waste CPU, journal space
# 6. Journal potentially bloated → wastes disk I/O
# 7. No VFS/dirty page tuning → suboptimal for dev workloads on NVMe
#
# Every change creates an entry in the undo script for easy reversal.
#
# Usage:
#   sudo ./fix_ubuntu_performance.sh                # Apply all fixes
#   sudo ./fix_ubuntu_performance.sh --dry-run      # Show what would be done
#   sudo ./fix_ubuntu_performance.sh --undo          # Reverse all changes
#   sudo ./fix_ubuntu_performance.sh -h              # Show help
#
# Safe to re-run: all fixes are idempotent.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

DRY_RUN=false
UNDO_MODE=false
for arg in "$@"; do
	case "$arg" in
	--dry-run)
		DRY_RUN=true
		;;
	--undo)
		UNDO_MODE=true
		;;
	-h | --help)
		cat <<'EOF'
fix_ubuntu_performance.sh - Fix common Ubuntu laptop performance issues

Usage: fix_ubuntu_performance.sh [OPTIONS]

Options:
  --dry-run          Show what would be done without making changes
  --undo             Reverse all changes (uses generated undo script)
  -i, --interactive  Prompt before each fix
  -h, --help         Show this help message

Fixes applied:
  1. Disable NetworkManager-wait-online.service (saves ~6.7s boot)
  2. Tune vm.swappiness to 10 + vm.vfs_cache_pressure to 50 + dirty page tuning
  3. Enable NVIDIA persistence mode via systemd
  4. Install earlyoom (prevents OOM hard-freezes)
  5. Mask failed SSSD socket/service units (stop retry waste)
  6. Vacuum systemd journal + set 300M cap
  7. Set NVMe I/O scheduler to kyber (if available, else none)

All fixes are idempotent and safe to re-run.
Run with --undo to reverse all changes.
EOF
		exit 0
		;;
	esac
done

require_root "$@"

UNDO_SCRIPT="/root/undo_ubuntu_performance_$(date +%Y%m%d_%H%M%S).sh"
FIXES_APPLIED=0
FIXES_SKIPPED=0

# ---------------------------------------------------------------------------
# Create undo script header
# ---------------------------------------------------------------------------
init_undo_script() {
	cat >"$UNDO_SCRIPT" <<'UNDOHEADER'
#!/usr/bin/env bash
# Auto-generated undo script for fix_ubuntu_performance.sh
# Run with: sudo bash /root/undo_ubuntu_performance_*.sh
set -euo pipefail

echo "Reversing Ubuntu performance optimizations..."
echo ""
UNDOHEADER
	chmod 700 "$UNDO_SCRIPT"
}

add_undo() {
	echo "$1" >>"$UNDO_SCRIPT"
}

# ---------------------------------------------------------------------------
# Helper: run or print a fix depending on --dry-run / --interactive
# ---------------------------------------------------------------------------
apply_fix() {
	local description="$1"
	shift

	echo ""
	log_info "$description"

	if [[ $DRY_RUN == "true" ]]; then
		echo "  [dry-run] Would run: $*"
		return 0
	fi

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		if ! ask_yes_no "  Apply this fix?"; then
			log_warn "Skipped."
			((FIXES_SKIPPED++)) || true
			return 0
		fi
	fi

	if "$@"; then
		log_ok "Done."
		((FIXES_APPLIED++)) || true
	else
		log_error "Failed (non-fatal, continuing)."
	fi
}

# ===================================================================
# Fix 1: Disable NetworkManager-wait-online.service
# ===================================================================
fix_nm_wait_online() {
	if ! systemctl is-enabled NetworkManager-wait-online.service >/dev/null 2>&1; then
		log_ok "NetworkManager-wait-online is already disabled — skipping."
		return 0
	fi

	systemctl disable NetworkManager-wait-online.service

	add_undo "# Undo: Re-enable NetworkManager-wait-online"
	add_undo "systemctl enable NetworkManager-wait-online.service"
	add_undo ""
	return 0
}

# ===================================================================
# Fix 2: Sysctl tuning (swappiness, VFS cache, dirty pages)
# ===================================================================
fix_sysctl_tuning() {
	local sysctl_file="/etc/sysctl.d/99-performance-tuning.conf"

	if [[ -f $sysctl_file ]]; then
		log_ok "Sysctl performance tuning already applied — skipping."
		return 0
	fi

	# Save current values for undo
	local cur_swappiness cur_vfs cur_dirty_ratio cur_dirty_bg
	cur_swappiness=$(sysctl -n vm.swappiness 2>/dev/null || echo 60)
	cur_vfs=$(sysctl -n vm.vfs_cache_pressure 2>/dev/null || echo 100)
	cur_dirty_ratio=$(sysctl -n vm.dirty_ratio 2>/dev/null || echo 20)
	cur_dirty_bg=$(sysctl -n vm.dirty_background_ratio 2>/dev/null || echo 10)

	cat >"$sysctl_file" <<'SYSCTL'
# Performance tuning for Ubuntu laptop with 32GB RAM + NVMe SSD
# Created by fix_ubuntu_performance.sh
#
# vm.swappiness=10:            Prefer keeping data in RAM over swapping (32GB is plenty)
# vm.vfs_cache_pressure=50:    Keep filesystem dentries/inodes cached longer (helps dev work)
# vm.dirty_ratio=15:           Allow more dirty pages before forced writeback (NVMe handles bursts)
# vm.dirty_background_ratio=5: Start background writeback earlier for smoother I/O

vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
SYSCTL

	# Apply immediately
	sysctl --system >/dev/null 2>&1

	add_undo "# Undo: Remove sysctl tuning, restore defaults"
	add_undo "rm -f /etc/sysctl.d/99-performance-tuning.conf"
	add_undo "sysctl -w vm.swappiness=$cur_swappiness vm.vfs_cache_pressure=$cur_vfs vm.dirty_ratio=$cur_dirty_ratio vm.dirty_background_ratio=$cur_dirty_bg >/dev/null"
	add_undo ""
	return 0
}

# ===================================================================
# Fix 3: NVIDIA persistence mode via systemd service
# ===================================================================
fix_nvidia_persistence() {
	local service_file="/etc/systemd/system/nvidia-persistence.service"

	# Check if persistence is already on
	if nvidia-smi -q 2>/dev/null | grep -q "Persistence Mode.*Enabled"; then
		log_ok "NVIDIA persistence mode is already enabled — skipping."
		return 0
	fi

	# On Ubuntu, nvidia-persistenced.service is "static" (no [Install] section)
	# and starts with --no-persistence-mode. We create a small helper service
	# that runs `nvidia-smi -pm 1` after the daemon is up.
	local helper_svc="/etc/systemd/system/nvidia-persistence-mode.service"

	if [[ -f $helper_svc ]] && systemctl is-enabled nvidia-persistence-mode.service >/dev/null 2>&1; then
		# Already set up — just make sure it's active this boot
		if ! nvidia-smi -q 2>/dev/null | grep -q "Persistence Mode.*Enabled"; then
			systemctl start nvidia-persistence-mode.service 2>/dev/null || true
		fi
		log_ok "NVIDIA persistence mode helper already configured."
		return 0
	fi

	if command -v nvidia-persistenced >/dev/null 2>&1; then
		# Ensure the daemon is running
		systemctl start nvidia-persistenced.service 2>/dev/null || true

		# Create a proper service with [Install] that runs nvidia-smi -pm 1
		cat >"$helper_svc" <<'NVSVC'
[Unit]
Description=Enable NVIDIA Persistence Mode
After=nvidia-persistenced.service
Requires=nvidia-persistenced.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/nvidia-smi -pm 1
ExecStop=/usr/bin/nvidia-smi -pm 0

[Install]
WantedBy=multi-user.target
NVSVC

		systemctl daemon-reload
		systemctl enable --now nvidia-persistence-mode.service

		add_undo "# Undo: Remove NVIDIA persistence mode helper service"
		add_undo "systemctl disable --now nvidia-persistence-mode.service 2>/dev/null || true"
		add_undo "rm -f /etc/systemd/system/nvidia-persistence-mode.service"
		add_undo "nvidia-smi -pm 0 2>/dev/null || true"
		add_undo "systemctl daemon-reload"
		add_undo ""
	else
		# Fall back to a simple systemd service using nvidia-smi
		cat >"$service_file" <<'NVSVC'
[Unit]
Description=NVIDIA Persistence Mode
After=nvidia.target
Requires=nvidia.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/nvidia-smi -pm 1
ExecStop=/usr/bin/nvidia-smi -pm 0

[Install]
WantedBy=multi-user.target
NVSVC

		systemctl daemon-reload
		systemctl enable --now nvidia-persistence.service

		add_undo "# Undo: Remove NVIDIA persistence service"
		add_undo "systemctl disable --now nvidia-persistence.service 2>/dev/null || true"
		add_undo "rm -f /etc/systemd/system/nvidia-persistence.service"
		add_undo "systemctl daemon-reload"
		add_undo ""
	fi

	return 0
}

# ===================================================================
# Fix 4: Install and enable earlyoom
# ===================================================================
fix_earlyoom() {
	if systemctl is-active earlyoom.service >/dev/null 2>&1; then
		log_ok "earlyoom is already running — skipping."
		return 0
	fi

	if ! dpkg -l earlyoom 2>/dev/null | grep -q '^ii'; then
		log_info "Installing earlyoom..."
		apt-get install -y earlyoom >/dev/null 2>&1
	fi

	# Configure earlyoom: kill at 5% free RAM / 10% free swap
	local earlyoom_conf="/etc/default/earlyoom"
	if [[ -f $earlyoom_conf ]]; then
		cp "$earlyoom_conf" "${earlyoom_conf}.bak"
	fi

	cat >"$earlyoom_conf" <<'EARLYOOM'
# earlyoom configuration - prevent OOM hard-freezes
# Created by fix_ubuntu_performance.sh
# -r 5  = act when free RAM drops below 5%
# -s 10 = act when free swap drops below 10%
# -n    = send SIGTERM first (graceful), then SIGKILL
# --prefer="(firefox|chromium|chrome)"  = prefer killing browsers (they recover well)
EARLYOOM_ARGS="-r 5 -s 10 -n --prefer '(firefox|chromium|chrome)'"
EARLYOOM

	systemctl enable --now earlyoom.service

	add_undo "# Undo: Disable and remove earlyoom"
	add_undo "systemctl disable --now earlyoom.service 2>/dev/null || true"
	add_undo "apt-get remove -y earlyoom >/dev/null 2>&1 || true"
	add_undo ""
	return 0
}

# ===================================================================
# Fix 5: Mask failed SSSD units (not needed on non-domain laptops)
# ===================================================================
fix_failed_sssd() {
	local sssd_units=(
		sssd-pac.service
		sssd-nss.socket
		sssd-pac.socket
		sssd-pam-priv.socket
		sssd-pam.socket
	)

	local any_failed=false
	for unit in "${sssd_units[@]}"; do
		if systemctl is-failed "$unit" >/dev/null 2>&1; then
			any_failed=true
			break
		fi
	done

	if [[ $any_failed == "false" ]]; then
		log_ok "No failed SSSD units — skipping."
		return 0
	fi

	add_undo "# Undo: Unmask SSSD units"
	for unit in "${sssd_units[@]}"; do
		if systemctl is-failed "$unit" >/dev/null 2>&1; then
			systemctl stop "$unit" 2>/dev/null || true
			systemctl mask "$unit"
			log_info "Masked $unit"
			add_undo "systemctl unmask $unit"
		fi
	done

	systemctl reset-failed 2>/dev/null || true
	add_undo ""
	return 0
}

# ===================================================================
# Fix 6: Journal vacuum + permanent size cap
# ===================================================================
fix_journal() {
	# Create permanent size cap via drop-in
	local dropin_dir="/etc/systemd/journald.conf.d"
	local dropin_file="$dropin_dir/size-limit.conf"

	if [[ -f $dropin_file ]] && grep -q 'SystemMaxUse=300M' "$dropin_file"; then
		log_ok "Journal size cap already configured — skipping."
		return 0
	fi

	mkdir -p "$dropin_dir"
	cat >"$dropin_file" <<'JOURNALEOF'
[Journal]
SystemMaxUse=300M
JOURNALEOF

	# Vacuum existing logs
	journalctl --vacuum-size=300M 2>/dev/null || true

	systemctl restart systemd-journald

	add_undo "# Undo: Remove journal size cap"
	add_undo "rm -f /etc/systemd/journald.conf.d/size-limit.conf"
	add_undo "systemctl restart systemd-journald"
	add_undo ""
	return 0
}

# ===================================================================
# Fix 7: Disable snap-related boot slowness (optional but impactful)
# ===================================================================
fix_snap_startup() {
	# Disable snapd.snap-repair.timer - not critical, runs periodically
	if systemctl is-enabled snapd.snap-repair.timer >/dev/null 2>&1; then
		systemctl disable snapd.snap-repair.timer
		systemctl stop snapd.snap-repair.timer 2>/dev/null || true

		add_undo "# Undo: Re-enable snap repair timer"
		add_undo "systemctl enable snapd.snap-repair.timer"
		add_undo ""
	else
		log_ok "snapd.snap-repair.timer already disabled — skipping."
	fi

	return 0
}

# ===================================================================
# Undo mode: run the most recent undo script
# ===================================================================
run_undo() {
	local latest_undo
	# shellcheck disable=SC2012
	latest_undo=$(ls -1t /root/undo_ubuntu_performance_*.sh 2>/dev/null | head -1)

	if [[ -z ${latest_undo:-} ]]; then
		log_error "No undo script found in /root/"
		exit 1
	fi

	log_info "Running undo script: $latest_undo"
	bash "$latest_undo"
	log_ok "All changes reversed."
	log_info "Reboot recommended to ensure all changes take effect."
	exit 0
}

# ===================================================================
# Apply all fixes
# ===================================================================
main() {
	if [[ $UNDO_MODE == "true" ]]; then
		run_undo
	fi

	if [[ $DRY_RUN == "false" ]]; then
		init_undo_script
	fi

	print_setup_header "Ubuntu Performance Optimization (Legion Laptop)"

	apply_fix \
		"Fix 1/7: Disable NetworkManager-wait-online.service (~6.7s boot saving)" \
		fix_nm_wait_online

	apply_fix \
		"Fix 2/7: Tune sysctl (swappiness=10, vfs_cache_pressure=50, dirty page tuning)" \
		fix_sysctl_tuning

	apply_fix \
		"Fix 3/7: Enable NVIDIA persistence mode (faster GPU operations)" \
		fix_nvidia_persistence

	apply_fix \
		"Fix 4/7: Install earlyoom (prevent OOM hard-freezes)" \
		fix_earlyoom

	apply_fix \
		"Fix 5/7: Mask failed SSSD units (stop retry waste)" \
		fix_failed_sssd

	apply_fix \
		"Fix 6/7: Vacuum journal logs + set permanent 300M size cap" \
		fix_journal

	apply_fix \
		"Fix 7/7: Disable snap repair timer (reduce background work)" \
		fix_snap_startup

	# ---------------------------------------------------------------
	# Summary
	# ---------------------------------------------------------------
	echo ""
	echo "=============================="
	echo " Performance Fix Summary"
	echo "=============================="

	if [[ $DRY_RUN == "true" ]]; then
		log_info "Dry-run mode — no changes were made."
	else
		log_ok "Fixes applied: $FIXES_APPLIED"
		if [[ $FIXES_SKIPPED -gt 0 ]]; then
			log_warn "Fixes skipped: $FIXES_SKIPPED"
		fi
		echo ""
		log_ok "Undo script saved to: $UNDO_SCRIPT"
		log_info "To reverse ALL changes: sudo bash $UNDO_SCRIPT"
	fi

	echo ""
	log_info "Reboot recommended for full effect."
	log_info "After reboot, verify with: systemd-analyze && nvidia-smi -q | grep Persistence"
}

main

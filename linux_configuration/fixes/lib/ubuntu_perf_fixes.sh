#!/bin/bash
# sysctl, NVIDIA persistence and earlyoom performance fixes.
#
# Sourced by fix_ubuntu_performance.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

# ===================================================================
# Fix 2: Sysctl tuning (swappiness, VFS cache, dirty pages)
# ===================================================================
fix_sysctl_tuning() {
	# SYSCTL_DROPIN_DIR and the other overrides below default to the real
	# locations; only the test harness sets them. The add_undo lines keep
	# their literal /etc paths on purpose -- the undo script runs on the
	# real system, not in the sandbox.
	local sysctl_file="${SYSCTL_DROPIN_DIR:-/etc/sysctl.d}/99-performance-tuning.conf"

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
	local service_file="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}/nvidia-persistence.service"

	# Check if persistence is already on
	if nvidia-smi -q 2>/dev/null | grep -q "Persistence Mode.*Enabled"; then
		log_ok "NVIDIA persistence mode is already enabled — skipping."
		return 0
	fi

	# On Ubuntu, nvidia-persistenced.service is "static" (no [Install] section)
	# and starts with --no-persistence-mode. We create a small helper service
	# that runs `nvidia-smi -pm 1` after the daemon is up.
	local helper_svc="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}/nvidia-persistence-mode.service"

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
	local earlyoom_conf="${EARLYOOM_CONF_FILE:-/etc/default/earlyoom}"
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

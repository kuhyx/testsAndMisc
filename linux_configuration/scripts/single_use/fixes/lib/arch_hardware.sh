#!/bin/bash
# fstrim, NVIDIA and CPU mitigation tweaks.
#
# Sourced by optimize_arch_desktop.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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

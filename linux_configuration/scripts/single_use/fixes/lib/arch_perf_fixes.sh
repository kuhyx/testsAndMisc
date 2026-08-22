#!/bin/bash
# Journal, NetworkManager and media-organizer performance fixes.
#
# Sourced by fix_arch_performance.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

# ===================================================================
# Fix 3: Journal vacuum + permanent size cap
# ===================================================================
fix_journal() {
	local usage_line
	usage_line=$(journalctl --disk-usage 2>/dev/null || true)

	local needs_vacuum=false
	# Optional space before the unit: journalctl prints "305.5M in the file
	# system", with no separator, so requiring one made this dead code.
	if [[ $usage_line =~ ([0-9]+\.?[0-9]*)\ ?G ]]; then
		needs_vacuum=true
	fi

	if [[ $needs_vacuum == "true" ]]; then
		journalctl --vacuum-size=300M
	else
		log_ok "Journal is already under 1GiB."
	fi

	# Create permanent size cap via drop-in
	local dropin_dir="${JOURNALD_CONF_DIR:-/etc/systemd/journald.conf.d}"
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
# Fix 4: Disable NetworkManager-wait-online
# ===================================================================
fix_nm_wait_online() {
	if ! systemctl is-enabled NetworkManager-wait-online.service >/dev/null 2>&1; then
		log_ok "NetworkManager-wait-online is already disabled — skipping."
		return 0
	fi

	systemctl disable NetworkManager-wait-online.service
	return 0
}

# ===================================================================
# Fix 5: media-organizer.service
# ===================================================================
fix_media_organizer() {
	local service_file="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}/media-organizer.service"

	# Find the organize_downloads.sh script
	local script_path=""
	local candidates=(
		"${ORGANIZE_SCRIPT_CANDIDATES:-/home/kuhy/testsAndMisc/linux_configuration/scripts/utils/organize_downloads.sh}"
		"/home/kuhy/linux-configuration/scripts/utils/organize_downloads.sh"
	)
	for candidate in "${candidates[@]}"; do
		if [[ -f $candidate ]]; then
			script_path="$candidate"
			break
		fi
	done

	if [[ -z $script_path ]]; then
		log_warn "organize_downloads.sh not found — skipping media-organizer fix."
		return 0
	fi

	local target_user="${SUDO_USER:-kuhy}"

	# Check if already correct
	if [[ -f $service_file ]]; then
		if grep -q "User=$target_user" "$service_file" &&
			grep -q "ExecStart=$script_path" "$service_file"; then
			log_ok "media-organizer.service is already correctly configured — skipping."
			return 0
		fi
	fi

	systemctl stop media-organizer.service 2>/dev/null || true

	cat >"$service_file" <<EOF
[Unit]
Description=Media File Organizer
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=oneshot
User=$target_user
Group=$target_user
ExecStart=$script_path
StandardOutput=journal
StandardError=journal
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
EOF

	systemctl daemon-reload
	systemctl reset-failed media-organizer.service 2>/dev/null || true
	systemctl enable media-organizer.service
	return 0
}

# ===================================================================
# Apply all fixes
# ===================================================================

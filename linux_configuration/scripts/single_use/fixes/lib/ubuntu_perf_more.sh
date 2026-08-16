#!/bin/bash
# Journal, sssd and snap-startup performance fixes.
#
# Sourced by fix_ubuntu_performance.sh; split out to keep ubuntu_perf_fixes.sh
# under the 250-line cap. Sourced rather than run, so it inherits the
# caller's strict mode and the variables above the source line.

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

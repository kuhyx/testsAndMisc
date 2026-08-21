#!/usr/bin/env bash
# lib/services_browser.sh — checks whose subject is a browser policy, a VM
# hosts-enforcement marker, or the per-user workout locker service.
#
# Sourced by check_and_enable_services.sh. check_workout_locker queries a USER
# unit from root and must go through user_systemctl (see its comment) rather
# than `sudo -u ... systemctl --user`.

# Absolute paths the checks below probe are prefixed with $SYSROOT, which is
# empty in production and a fixture tree under test. It is deliberately NOT
# defaulted here: several repairs in this family write outside `run` (chattr,
# find -delete, an append to resolved.conf), so a test that forgot to set it
# would edit the real /etc. Unset is a hard error; empty is the real filesystem.
SYSROOT="${SERVICES_ROOT?SERVICES_ROOT must be set (empty = the real filesystem)}"

check_guest_mode_removal() {
	header "Chromium Guest Mode Removal"

	local status="ok"
	local issues=()

	# Check if managed policy files exist for any browser
	local policy_found=false
	for policy_dir in \
		"${SYSROOT}/etc/chromium/policies/managed" \
		"${SYSROOT}/etc/opt/chrome/policies/managed" \
		"${SYSROOT}/etc/thorium/policies/managed" \
		"${SYSROOT}/etc/brave/policies/managed"; do
		if [[ -d $policy_dir ]] && ls "$policy_dir"/*.json &>/dev/null 2>&1; then
			# Check for guest mode policy
			if grep -rl 'BrowserGuestModeEnabled' "$policy_dir" &>/dev/null 2>&1; then
				msg "Guest mode policy found in $policy_dir"
				policy_found=true
			fi
		fi
	done

	if [[ $policy_found == false ]]; then
		# Only flag as issue if a Chromium browser is actually installed
		if command -v thorium-browser &>/dev/null || command -v chromium &>/dev/null || command -v google-chrome &>/dev/null || command -v brave-browser &>/dev/null; then
			issues+=("No guest mode removal policies found for installed browsers")
			status="error"
		else
			note "No Chromium-based browsers detected, skipping"
		fi
	fi

	if [[ $status != "ok" ]]; then
		for issue in "${issues[@]}"; do
			err "$issue"
		done
		((ISSUES_FOUND++)) || true

		if [[ $STATUS_ONLY -eq 0 ]]; then
			note "Removing guest mode..."
			if [[ -f $REMOVE_GUEST_MODE_SCRIPT ]]; then
				run bash "$REMOVE_GUEST_MODE_SCRIPT"
				((FIXES_APPLIED++)) || true
			else
				err_missing_script "Script not found: $REMOVE_GUEST_MODE_SCRIPT"
			fi
		fi
	fi

	set_service_status "guest_mode_removal" "$status"
}

check_vbox_hosts() {
	header "VirtualBox Hosts Enforcement"

	local status="ok"
	local issues=()

	# Only check if VirtualBox is installed.
	# This is NOT "skipped" in the sense of ducking a check: VirtualBox is absent
	# AND deliberately blocked by pacman policy — pacman_blocked_keywords.txt lists
	# virtualbox/vbox with the comment "can bypass /etc/hosts restrictions", which
	# is the very thing this check enforces. With no VirtualBox there are no VMs to
	# enforce /etc/hosts inside, so the check is genuinely not applicable. Report
	# n/a so it reads as deliberate rather than something that got ducked.
	if ! command -v VBoxManage &>/dev/null; then
		note "VirtualBox not installed (blocked by pacman policy) — not applicable"
		set_service_status "vbox_hosts" "n/a"
		return
	fi

	# Check if enforcement marker exists
	if [[ -f "${SYSROOT}/var/lib/vbox-hosts-enforced" ]]; then
		msg "VirtualBox hosts enforcement marker exists"
	else
		issues+=("VirtualBox hosts enforcement not applied")
		status="error"
	fi

	if [[ $status != "ok" ]]; then
		for issue in "${issues[@]}"; do
			err "$issue"
		done
		((ISSUES_FOUND++)) || true

		if [[ $STATUS_ONLY -eq 0 ]]; then
			note "Enforcing hosts in VirtualBox VMs..."
			if [[ -f $VBOX_HOSTS_SCRIPT ]]; then
				run bash "$VBOX_HOSTS_SCRIPT"
				((FIXES_APPLIED++)) || true
			else
				err_missing_script "Script not found: $VBOX_HOSTS_SCRIPT"
			fi
		fi
	fi

	set_service_status "vbox_hosts" "$status"
}

check_workout_locker() {
	header "Workout Lock Screen"

	local status="ok"
	local issues=()
	local user="${SUDO_USER:-$USER}"

	# Check screen_lock.py script exists
	if [[ -f $WORKOUT_LOCKER_SCRIPT ]]; then
		msg "screen_lock.py exists at $WORKOUT_LOCKER_SCRIPT"
	else
		issues+=("screen_lock.py not found at $WORKOUT_LOCKER_SCRIPT")
		status="error"
	fi

	# Check user service is enabled
	if user_systemctl "$user" is-enabled workout-locker.service &>/dev/null 2>&1; then
		msg "workout-locker.service is enabled (user service)"
	else
		issues+=("workout-locker.service is not enabled (user service)")
		status="error"
	fi

	# Check user service is active (advisory — it only runs at login)
	if user_systemctl "$user" is-active workout-locker.service &>/dev/null 2>&1; then
		msg "workout-locker.service is active"
	else
		issues+=("workout-locker.service is not active (expected at login time)")
		if [[ $status != "error" ]]; then status="warning"; fi
	fi

	if [[ $status != "ok" ]]; then
		for issue in "${issues[@]}"; do
			if [[ $status == "error" ]]; then
				err "$issue"
			else
				warn "$issue"
			fi
		done
		((ISSUES_FOUND++)) || true

		if [[ $STATUS_ONLY -eq 0 && $status == "error" ]]; then
			note "Installing workout locker service..."
			if [[ -f $WORKOUT_LOCKER_INSTALL_SCRIPT ]]; then
				run sudo -u "$user" bash "$WORKOUT_LOCKER_INSTALL_SCRIPT"
				((FIXES_APPLIED++)) || true
				# Re-verify
				if [[ $DRY_RUN -eq 0 ]] && user_systemctl "$user" is-enabled workout-locker.service &>/dev/null 2>&1; then
					status="ok"
				fi
			else
				err_missing_script "Install script not found: $WORKOUT_LOCKER_INSTALL_SCRIPT"
			fi
		fi
	fi

	set_service_status "workout_locker" "$status"
}

#!/usr/bin/env bash
# lib/services_apps.sh — per-application blocking checks (messaging-app launch
# wrappers, and the LeechBlock browser extension for the invoking user).
#
# Sourced by check_and_enable_services.sh.

# Absolute paths the checks below probe are prefixed with $SYSROOT, which is
# empty in production and a fixture tree under test. It is deliberately NOT
# defaulted here: several repairs in this family write outside `run` (chattr,
# find -delete, an append to resolved.conf), so a test that forgot to set it
# would edit the real /etc. Unset is a hard error; empty is the real filesystem.
SYSROOT="${SERVICES_ROOT?SERVICES_ROOT must be set (empty = the real filesystem)}"

check_compulsive_blocker() {
	header "Compulsive Opening Blocker"

	local status="ok"
	local issues=()

	# Check if main script is installed
	if [[ -f "${SYSROOT}/usr/local/bin/block-compulsive-opening.sh" ]]; then
		msg "Blocker script installed at ${SYSROOT}/usr/local/bin/block-compulsive-opening.sh"
	else
		issues+=("block-compulsive-opening.sh not found in ${SYSROOT}/usr/local/bin")
		status="error"
	fi

	# Check if wrappers are installed for known apps
	local checked_any=false
	local stale=()
	for app in beeper signal-desktop discord; do
		local wrapper_path="${SYSROOT}/usr/bin/$app"
		local owned=0
		_pkg_owns_path "/usr/bin/$app" || owned=$?
		if [[ -f "${wrapper_path}.orig" && $owned -eq 1 ]]; then
			# Package removed: pacman deleted the wrapper but not the backup,
			# so `<app>.orig` still launches the app around the blocker.
			issues+=("stale $app.orig left after package removal")
			stale+=("$app")
			if [[ $status != "error" ]]; then status="warning"; fi
			checked_any=true
		elif [[ -f "${wrapper_path}.orig" ]] || [[ -L "$wrapper_path" ]]; then
			if [[ -f "${wrapper_path}.orig" ]]; then
				msg "$app wrapper installed (original backed up)"
				checked_any=true
			fi
		elif command -v "$app" &>/dev/null; then
			issues+=("$app is installed but wrapper not applied")
			if [[ $status != "error" ]]; then status="warning"; fi
			checked_any=true
		fi
	done

	if [[ $checked_any == false && $status == "ok" ]]; then
		note "No target apps (beeper, signal-desktop, discord) found on system"
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
			note "Installing compulsive opening blocker..."
			if [[ -f $COMPULSIVE_BLOCK_SCRIPT ]]; then
				run bash "$COMPULSIVE_BLOCK_SCRIPT" install
				((FIXES_APPLIED++)) || true
			else
				err_missing_script "Install script not found: $COMPULSIVE_BLOCK_SCRIPT"
			fi
		fi

		# A stale backup is repaired on its own, whatever the status: the full
		# installer is only for a missing blocker.
		if [[ $STATUS_ONLY -eq 0 ]]; then
			for app in "${stale[@]}"; do
				local stale_path="${SYSROOT}/usr/bin/$app"
				note "Removing stale ${stale_path}.orig..."
				run rm -f "${stale_path}.orig"
				# A wrapper left behind would exec the .orig just deleted.
				if grep -q "block-compulsive-opening" "$stale_path" 2>/dev/null; then
					run rm -f "$stale_path"
				fi
				((FIXES_APPLIED++)) || true
			done
		fi
	fi

	set_service_status "compulsive_blocker" "$status"
}

# Does an installed package own <abs-path>? Read from ${SYSROOT}'s pacman db
# rather than `pacman -Qqo`, so it honours SYSROOT and skips the pacman
# wrapper. grep's exit code is the answer: 0 owned, 1 unowned, 2 undeterminable
# (no db) -- only a definite 1 makes a .orig stale.
_pkg_owns_path() { # <abs-path>
	local lists=("${SYSROOT}"/var/lib/pacman/local/*/files)
	[[ -e ${lists[0]} ]] || return 2
	local rc=0
	grep -qxF -- "${1#/}" "${lists[@]}" 2>/dev/null || rc=$?
	return "$rc"
}

check_leechblock() {
	header "LeechBlock Browser Extension"

	local status="ok"
	local issues=()
	local user="${SUDO_USER:-$USER}"
	local user_home
	user_home="${SYSROOT}/home/$user"

	# Check if LeechBlock is installed for any browser
	local leechblock_dir="$user_home/.local/share/leechblockng"
	if [[ -d $leechblock_dir ]]; then
		msg "LeechBlock directory exists at $leechblock_dir"
	else
		issues+=("LeechBlock not found at $leechblock_dir")
		status="error"
	fi

	# Check for browser wrappers with LeechBlock
	local found_wrapper=false
	for desktop_file in "$user_home/.local/share/applications/"*leechblock* "$user_home/.local/share/applications/"*LeechBlock*; do
		if [[ -f $desktop_file ]]; then
			msg "LeechBlock desktop entry found: $(basename "$desktop_file")"
			found_wrapper=true
		fi
	done

	if [[ $found_wrapper == false && -d $leechblock_dir ]]; then
		issues+=("No LeechBlock desktop entries found")
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
			note "Installing LeechBlock..."
			if [[ -f $LEECHBLOCK_SCRIPT ]]; then
				run sudo -u "$user" bash "$LEECHBLOCK_SCRIPT"
				((FIXES_APPLIED++)) || true
			else
				err_missing_script "Install script not found: $LEECHBLOCK_SCRIPT"
			fi
		fi
	fi

	set_service_status "leechblock" "$status"
}

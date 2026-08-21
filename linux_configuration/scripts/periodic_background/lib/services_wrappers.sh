#!/usr/bin/env bash
# lib/services_wrappers.sh — pacman/makepkg wrapper deployment checks.
#
# Sourced by check_and_enable_services.sh. Each check verifies the symlink, the
# .orig backup, the installed files AND the install-time drift manifest, then
# reinstalls via the matching installer when STATUS_ONLY is off.

check_pacman_wrapper() {
	header "Pacman Wrapper"

	local status="ok"
	local issues=()

	# Check if wrapper is installed
	if [[ -L /usr/bin/pacman ]]; then
		local target
		target=$(readlink -f /usr/bin/pacman)
		if [[ $target == "/usr/local/bin/pacman_wrapper" ]]; then
			msg "Pacman symlink points to wrapper"
		else
			issues+=("Pacman symlink points to: $target (expected /usr/local/bin/pacman_wrapper)")
			status="error"
		fi
	else
		issues+=("Pacman is not a symlink (wrapper not installed)")
		status="error"
	fi

	# Check if original pacman is backed up
	if [[ -f /usr/bin/pacman.orig ]]; then
		msg "Original pacman backed up at /usr/bin/pacman.orig"
	else
		issues+=("Original pacman backup not found at /usr/bin/pacman.orig")
		status="error"
	fi

	# Check if wrapper script exists
	if [[ -f /usr/local/bin/pacman_wrapper ]]; then
		msg "Wrapper script exists at /usr/local/bin/pacman_wrapper"
	else
		issues+=("Wrapper script not found at /usr/local/bin/pacman_wrapper")
		status="error"
	fi

	# Check supporting files
	for file in words.txt pacman_blocked_keywords.txt pacman_whitelist.txt; do
		if [[ -f "/usr/local/bin/$file" ]]; then
			msg "Supporting file exists: /usr/local/bin/$file"
		else
			warn "Supporting file missing: /usr/local/bin/$file"
		fi
	done

	# Content drift — the check everything above misses. A correct symlink and a
	# present file say nothing about WHICH version is deployed.
	local drift_rc=0
	deployment_drift "$PACMAN_WRAPPER_MANIFEST" || drift_rc=$?
	case $drift_rc in
	0) msg "Wrapper matches the source it was installed from (no drift)" ;;
	1)
		issues+=("Deployed pacman wrapper differs from its install manifest (stale or tampered)")
		status="error"
		;;
	2)
		issues+=("No drift manifest at $PACMAN_WRAPPER_MANIFEST — deployed version unverifiable")
		status="error"
		;;
	esac

	# Report and fix
	if [[ $status == "error" ]]; then
		for issue in "${issues[@]}"; do
			err "$issue"
		done
		((ISSUES_FOUND++)) || true

		if [[ $STATUS_ONLY -eq 0 ]]; then
			note "Installing pacman wrapper..."
			if [[ -f $PACMAN_WRAPPER_INSTALL ]]; then
				run bash "$PACMAN_WRAPPER_INSTALL"
				((FIXES_APPLIED++)) || true
				# Re-verify after fix. Content is part of "fixed": a reinstall
				# that leaves the manifest failing has repaired nothing.
				if [[ $DRY_RUN -eq 0 ]] && [[ -L /usr/bin/pacman ]] && [[ -f /usr/bin/pacman.orig ]] &&
					[[ -f /usr/local/bin/pacman_wrapper ]] && deployment_drift "$PACMAN_WRAPPER_MANIFEST"; then
					status="ok"
				fi
			else
				err_missing_script "Installer script not found: $PACMAN_WRAPPER_INSTALL"
			fi
		fi
	fi

	set_service_status "pacman_wrapper" "$status"
}

check_makepkg_wrapper() {
	header "Makepkg Wrapper"

	local status="ok"
	local issues=()

	# Wrapper symlink
	if [[ -L /usr/bin/makepkg ]]; then
		local target
		target=$(readlink -f /usr/bin/makepkg)
		if [[ $target == "/usr/local/bin/makepkg_wrapper" ]]; then
			msg "Makepkg symlink points to wrapper"
		else
			issues+=("Makepkg symlink points to: $target (expected /usr/local/bin/makepkg_wrapper)")
			status="error"
		fi
	else
		issues+=("Makepkg is not a symlink (wrapper not installed)")
		status="error"
	fi

	# Original makepkg backup
	if [[ -f /usr/bin/makepkg.orig ]]; then
		msg "Original makepkg backed up at /usr/bin/makepkg.orig"
	else
		issues+=("Original makepkg backup not found at /usr/bin/makepkg.orig")
		status="error"
	fi

	# Wrapper, shared lib, rewrap helper, survival hook
	if [[ -f /usr/local/bin/makepkg_wrapper ]]; then
		msg "Wrapper script exists at /usr/local/bin/makepkg_wrapper"
	else
		issues+=("Wrapper script not found at /usr/local/bin/makepkg_wrapper")
		status="error"
	fi
	if [[ -f /usr/local/bin/pacman_lock_lib.sh ]]; then
		msg "Shared lock library exists at /usr/local/bin/pacman_lock_lib.sh"
	else
		issues+=("Shared lock library not found at /usr/local/bin/pacman_lock_lib.sh")
		status="error"
	fi
	if [[ -f /usr/local/bin/rewrap_pkg_managers.sh ]]; then
		msg "Rewrap helper exists at /usr/local/bin/rewrap_pkg_managers.sh"
	else
		issues+=("Rewrap helper not found at /usr/local/bin/rewrap_pkg_managers.sh")
		status="error"
	fi
	if [[ -f /etc/pacman.d/hooks/96-restore-pkg-wrappers.hook ]]; then
		msg "Upgrade-survival hook installed"
	else
		issues+=("Upgrade-survival hook not installed at /etc/pacman.d/hooks/96-restore-pkg-wrappers.hook")
		status="error"
	fi

	# Content drift (see check_pacman_wrapper for why existence is not enough)
	local drift_rc=0
	deployment_drift "$MAKEPKG_WRAPPER_MANIFEST" || drift_rc=$?
	case $drift_rc in
	0) msg "Makepkg wrapper matches the source it was installed from (no drift)" ;;
	1)
		issues+=("Deployed makepkg wrapper differs from its install manifest (stale or tampered)")
		status="error"
		;;
	2)
		issues+=("No drift manifest at $MAKEPKG_WRAPPER_MANIFEST — deployed version unverifiable")
		status="error"
		;;
	esac

	# Report and fix
	if [[ $status == "error" ]]; then
		for issue in "${issues[@]}"; do
			err "$issue"
		done
		((ISSUES_FOUND++)) || true

		if [[ $STATUS_ONLY -eq 0 ]]; then
			note "Installing makepkg wrapper..."
			if [[ -f $MAKEPKG_WRAPPER_INSTALL ]]; then
				run bash "$MAKEPKG_WRAPPER_INSTALL"
				((FIXES_APPLIED++)) || true
				if [[ $DRY_RUN -eq 0 ]] && [[ -L /usr/bin/makepkg ]] && [[ -f /usr/bin/makepkg.orig ]] && [[ -f /usr/local/bin/makepkg_wrapper ]]; then
					status="ok"
				fi
			else
				err_missing_script "Installer script not found: $MAKEPKG_WRAPPER_INSTALL"
			fi
		fi
	fi

	set_service_status "makepkg_wrapper" "$status"
}

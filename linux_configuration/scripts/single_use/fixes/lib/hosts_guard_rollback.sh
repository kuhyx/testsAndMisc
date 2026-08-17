#!/usr/bin/env bash
# Rollback state capture, rollback itself, and status reporting for the
# hosts-guard migration.
#
# Sourced by the entry script alongside hosts_guard_migrate.sh.

# ----------------------------------------------------------------------------
# Status
# ----------------------------------------------------------------------------
show_status() {
	printf "\n%s\n" "=== guard-lib instances ==="
	local name
	for name in "${INSTANCES[@]}"; do
		if instance_registered "$name"; then
			msg "$name registered"
			"$GUARDCTL" file-guard status "$name" 2>&1 | sed 's/^/      /'
		else
			warn "$name NOT registered"
		fi
	done

	printf "\n%s\n" "=== legacy pacman hooks ==="
	local hook
	for hook in "${LEGACY_HOOKS[@]}"; do
		if [[ -f "$HOOKS_DIR/$hook" ]]; then
			warn "$hook still present"
		else
			msg "$hook retired"
		fi
	done

	printf "\n%s\n" "=== legacy systemd units ==="
	local unit state
	for unit in "${LEGACY_UNITS[@]}"; do
		# `is-enabled` PRINTS the state but EXITS 1 for anything not enabled, so
		# `|| echo absent` would append a second line to a perfectly good answer.
		state="$(systemctl is-enabled "$unit" 2>/dev/null)" || true
		[[ -n $state ]] || state="absent"
		if [[ $state == "enabled" ]]; then
			warn "$unit is $state"
		else
			msg "$unit is $state"
		fi
	done
}

# ----------------------------------------------------------------------------
# Rollback state
# ----------------------------------------------------------------------------
save_rollback_state() {
	run mkdir -p "$STATE_DIR/hooks"

	local hook
	for hook in "${LEGACY_HOOKS[@]}"; do
		if [[ -f "$HOOKS_DIR/$hook" && ! -f "$STATE_DIR/hooks/$hook" ]]; then
			run cp -a "$HOOKS_DIR/$hook" "$STATE_DIR/hooks/$hook"
			note "backed up $hook"
		fi
	done

	# Record enablement so rollback restores the exact prior state rather than
	# guessing (resolved-guard.* were already disabled here, for instance).
	if [[ ! -f "$STATE_DIR/units.state" ]] && ((DRY_RUN == 0)); then
		local unit ustate
		for unit in "${LEGACY_UNITS[@]}"; do
			ustate="$(systemctl is-enabled "$unit" 2>/dev/null)" || true
			[[ -n $ustate ]] || ustate="absent"
			printf '%s=%s\n' "$unit" "$ustate"
		done >"$STATE_DIR/units.state"
		note "recorded legacy unit states in $STATE_DIR/units.state"
	fi
}

# ----------------------------------------------------------------------------
# Rollback
# ----------------------------------------------------------------------------
do_rollback() {
	[[ -d $STATE_DIR ]] || {
		err "no rollback state at $STATE_DIR - nothing to roll back to"
		exit 1
	}

	local name
	for name in "${INSTANCES[@]}"; do
		if instance_registered "$name"; then
			# Keep the canonical: it is the known-good copy of the file, and
			# the legacy layer re-snapshots from the live file, which may have
			# drifted. Losing it would turn a rollback into data loss.
			run "$GUARDCTL" file-guard uninstall "$name" --keep-canonical || true
			msg "uninstalled guard-lib instance $name"
		fi
	done

	local hook
	for hook in "${LEGACY_HOOKS[@]}"; do
		if [[ -f "$STATE_DIR/hooks/$hook" ]]; then
			run cp -a "$STATE_DIR/hooks/$hook" "$HOOKS_DIR/$hook"
			msg "restored $hook"
		fi
	done

	if [[ -f "$STATE_DIR/units.state" ]]; then
		local unit state
		while IFS='=' read -r unit state; do
			[[ $state == "enabled" ]] || continue
			run systemctl enable --now "$unit" 2>/dev/null || warn "could not re-enable $unit"
			msg "re-enabled $unit"
		done <"$STATE_DIR/units.state"
	else
		warn "no units.state recorded - legacy units left as-is"
	fi

	# Re-assert the legacy protections NOW rather than waiting for a watcher.
	# `guardctl file-guard uninstall` chattr -i's the target on its way out, and
	# the legacy *-guard.path units only fire on PathModified - so without this
	# a rolled-back /etc/hosts sits with NO immutable flag until something
	# happens to write to it. Caught by actually running --rollback and looking
	# at lsattr, which is the only reason it is handled at all.
	#
	# Order matters for hosts specifically: it is bind-mounted read-only, and
	# chattr cannot write through a ro mount. enforce-hosts.sh does a bare
	# `chattr +i` with no collapse (it relies on running before the mount at
	# boot), so it fails silently here unless the mount is dropped first. So:
	# collapse, enforce, then let the bind-mount unit rebuild the ro layer.
	collapse_mounts /etc/hosts

	local svc
	for svc in hosts-guard.service nsswitch-guard.service resolved-guard.service; do
		systemctl cat "$svc" &>/dev/null || continue
		run systemctl start "$svc" 2>/dev/null || warn "could not run $svc"
	done

	if systemctl cat hosts-bind-mount.service &>/dev/null; then
		run systemctl restart hosts-bind-mount.service 2>/dev/null || warn "could not restart hosts-bind-mount.service"
	fi
	msg "re-ran legacy enforcement (restores chattr +i and the ro bind mount)"

	printf "\n"
	msg "rollback complete"
	note "verify with: sudo $SCRIPT_NAME --status"
}

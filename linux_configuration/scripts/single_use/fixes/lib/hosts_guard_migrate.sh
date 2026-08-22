#!/usr/bin/env bash
# The migration and rollback steps for hosts-guard, plus their validation and
# status reporting.
#
# Sourced by the entry script, which owns the CLI and the instance registry.

# ----------------------------------------------------------------------------
# Preconditions
# ----------------------------------------------------------------------------
validate_requirements() {
	[[ -x $GUARDCTL ]] || {
		err "guardctl not found at $GUARDCTL - run guard-lib's install.sh first"
		exit 1
	}

	local unit
	for unit in guard-file@.path guard-file@.service guard-bind-mount@.service; do
		[[ -f "/etc/systemd/system/$unit" ]] || {
			err "missing systemd template /etc/systemd/system/$unit - run guard-lib's install.sh first"
			exit 1
		}
	done

	[[ -d $PLUGIN_SRC_DIR ]] || {
		err "plugin sources not found at $PLUGIN_SRC_DIR"
		exit 1
	}

	# A live transaction would race every chattr and umount below.
	if [[ -e /var/lib/pacman/db.lck ]]; then
		err "/var/lib/pacman/db.lck exists - a pacman transaction is in flight"
		exit 1
	fi
}

install_plugins() {
	run mkdir -p "$PLUGIN_INSTALL_DIR"
	local src
	for src in "$PLUGIN_SRC_DIR"/*.sh; do
		[[ -e $src ]] || continue
		run install -m 755 "$src" "$PLUGIN_INSTALL_DIR/$(basename "$src")"
	done
	msg "plugins installed to $PLUGIN_INSTALL_DIR"
}

# ----------------------------------------------------------------------------
# Migration
# ----------------------------------------------------------------------------
stop_legacy_units_for() { # <instance name>
	local prefix="$1"
	local unit
	for unit in "${LEGACY_UNITS[@]}"; do
		[[ $unit == "$prefix"-* ]] || continue
		systemctl list-unit-files "$unit" &>/dev/null || continue
		run systemctl disable --now "$unit" 2>/dev/null || true
	done
}

# Unmount every stacked bind layer so chattr can reach the real inode. Mirrors
# the legacy pacman-pre-unlock-hosts.sh, which had to do exactly this.
# Every branch is a full `if` and the function ends in an explicit `return 0`.
# The obvious `((i > 20)) && break` form leaves the loop body's exit status at 1
# whenever the arithmetic is false, and under `set -e` that aborted the whole
# rollback silently — but ONLY when the loop actually ran, so --dry-run and an
# already-unmounted target both looked fine. It cost a live /etc/hosts left with
# neither the immutable flag nor its read-only mount to notice.
collapse_mounts() { # <path>
	local target="$1" i=0
	while mountpoint -q "$target"; do
		if ! run umount -l "$target" 2>/dev/null; then
			break
		fi
		i=$((i + 1))
		if ((i > 20)); then
			break
		fi
		# Nothing is really unmounted under --dry-run, so `mountpoint` stays
		# true forever; report the intent once instead of 20 identical lines.
		if ((DRY_RUN == 1)); then
			break
		fi
	done
	return 0
}

migrate_instance() { # <name>
	local name="$1"
	local spec target bind plugin also_watch
	spec="$(instance_spec "$name")"
	IFS='|' read -r target bind plugin also_watch <<<"$spec"

	if instance_registered "$name"; then
		msg "$name already registered - skipping"
		return 0
	fi

	if [[ ! -e $target ]]; then
		warn "$name: target $target does not exist - skipping"
		return 0
	fi

	note "migrating $name ($target)"

	stop_legacy_units_for "$name"
	collapse_mounts "$target"
	run chattr -i "$target" 2>/dev/null || true

	local -a args=(file-guard install "$name" --target "$target")
	[[ $bind == "yes" ]] && args+=(--bind-mount)
	[[ -n $plugin ]] && args+=(--plugin "$PLUGIN_INSTALL_DIR/$plugin")
	[[ -n $also_watch ]] && args+=(--also-watch "$also_watch")

	run "$GUARDCTL" "${args[@]}"
	msg "$name migrated"
}

retire_legacy_hooks() {
	local hook removed=0
	for hook in "${LEGACY_HOOKS[@]}"; do
		if [[ -f "$HOOKS_DIR/$hook" ]]; then
			run rm -f "$HOOKS_DIR/$hook"
			msg "retired $hook"
			removed=1
		fi
	done
	((removed == 0)) && msg "legacy pacman hooks already retired"
	return 0
}

do_migrate() {
	validate_requirements
	save_rollback_state
	install_plugins

	local name
	for name in "${INSTANCES[@]}"; do
		migrate_instance "$name"
	done

	# Only retire the legacy hooks once guard-lib actually owns something -
	# otherwise a failed migration would leave the files with NO pacman
	# unlock hook at all, and the next transaction would fight chattr +i.
	local registered=0
	for name in "${INSTANCES[@]}"; do
		instance_registered "$name" && registered=$((registered + 1))
	done

	if ((registered == 0)) && ((DRY_RUN == 0)); then
		err "no guard-lib instance registered - refusing to retire the legacy hooks"
		exit 1
	fi

	retire_legacy_hooks

	printf "\n"
	msg "migration complete ($registered instance(s) registered)"
	note "verify with: sudo $SCRIPT_NAME --status"
	note "undo with:   sudo $SCRIPT_NAME --rollback"
}

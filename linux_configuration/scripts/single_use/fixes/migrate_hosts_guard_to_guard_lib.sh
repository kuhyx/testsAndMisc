#!/bin/bash

# ============================================================================
# migrate_hosts_guard_to_guard_lib.sh
#
# Completes the guard-lib migration that commit 66c4698 started but never
# finished on this machine.
#
# State this repairs: guard-lib is installed (guardctl, lib/, systemd templates,
# and BOTH generic pacman hooks) with /etc/guard-lib/targets completely empty,
# while the pre-guard-lib hosts-guard implementation still does all the real
# work through its own per-file pacman hooks and systemd units. So every pacman
# transaction runs two PreTransaction hooks where one would do, and the
# guard-lib pair - the one that runs FIRST, and the one present for all four
# recorded hook stalls - does literally nothing.
#
# After this runs there is one guard system: guardctl file-guard instances for
# hosts, nsswitch and resolved, driven by guard-lib's generic unlock-all /
# relock-all hooks. The legacy hooks and units are retired.
#
# NOT migrated here: the "shutdown-schedule" instance that
# setup_midnight_shutdown.sh registers. Its target /etc/shutdown-schedule.conf
# does not exist on this machine, so registering it would mean installing a
# different feature, not finishing this migration. Run that script if you want
# the midnight-shutdown guard.
#
# Every step is idempotent, and --rollback restores the legacy layer.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly GUARDCTL="/usr/local/bin/guardctl"
readonly TARGETS_DIR="/etc/guard-lib/targets"
readonly STATE_DIR="/var/lib/guard-lib-migration"
readonly HOOKS_DIR="/etc/pacman.d/hooks"
# Plugins must live somewhere permanent: guardctl records an ABSOLUTE plugin
# path in the instance conf, so pointing it at a repo checkout (or worse, a git
# worktree) silently breaks enforcement the day that directory moves.
readonly PLUGIN_INSTALL_DIR="/usr/local/share/guard-lib-plugins"

readonly LEGACY_HOOKS=(
	"10-unlock-etc-hosts.hook"
	"90-relock-etc-hosts.hook"
)
readonly LEGACY_UNITS=(
	"hosts-guard.path"
	"hosts-guard.service"
	"hosts-bind-mount.service"
	"nsswitch-guard.path"
	"nsswitch-guard.service"
	"resolved-guard.path"
	"resolved-guard.service"
)

DRY_RUN=0
MODE="migrate"

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
PLUGIN_SRC_DIR="$(readlink -f "$SCRIPT_DIR/../../periodic_background/hosts/guard/plugins")"
readonly PLUGIN_SRC_DIR

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

msg() { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
note() { printf "${BLUE}[i]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err() { printf "${RED}[✗]${NC} %s\n" "$*" >&2; }

usage() {
	cat <<EOF
Usage: sudo $SCRIPT_NAME [OPTIONS]

Finishes the guard-lib migration for /etc/hosts, /etc/nsswitch.conf and
/etc/systemd/resolved.conf, then retires the legacy hosts-guard layer.

Options:
      --rollback   Undo: uninstall the guard-lib instances, restore the legacy
                   pacman hooks and re-enable the legacy units.
      --status     Show what is currently registered; change nothing.
      --dry-run    Print what would happen; change nothing.
  -h, --help       Show this help
EOF
	exit 0
}

run() {
	if ((DRY_RUN == 1)); then
		printf "${YELLOW}DRY-RUN:${NC} %s\n" "$*"
		return 0
	fi
	"$@"
}

require_root() {
	if [[ $EUID -ne 0 ]]; then
		exec sudo -E bash "$0" "$@"
	fi
}

# ----------------------------------------------------------------------------
# Instance table: name | target | bind_mount | plugin basename | also_watch
# ----------------------------------------------------------------------------
instance_spec() { # <name> -> echoes "target|bind|plugin|also_watch"
	case "$1" in
	hosts) echo "/etc/hosts|yes||" ;;
	nsswitch) echo "/etc/nsswitch.conf|no|nsswitch-plugin.sh|" ;;
	resolved) echo "/etc/systemd/resolved.conf|no|resolved-plugin.sh|/etc/systemd/resolved.conf.d" ;;
	*) return 1 ;;
	esac
}

readonly INSTANCES=(hosts nsswitch resolved)

instance_registered() { [[ -f "$TARGETS_DIR/$1.conf" ]]; }

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

# Parse arguments
require_root "$@"

while [[ $# -gt 0 ]]; do
	case "$1" in
	--rollback)
		MODE="rollback"
		shift
		;;
	--status)
		MODE="status"
		shift
		;;
	--dry-run)
		DRY_RUN=1
		shift
		;;
	-h | --help)
		usage
		;;
	*)
		err "Unknown option: $1"
		exit 1
		;;
	esac
done

case "$MODE" in
migrate) do_migrate ;;
rollback) do_rollback ;;
status) show_status ;;
esac

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

# shellcheck source=lib/hosts_guard_migrate.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hosts_guard_migrate.sh"
# shellcheck source=lib/hosts_guard_rollback.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hosts_guard_rollback.sh"

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

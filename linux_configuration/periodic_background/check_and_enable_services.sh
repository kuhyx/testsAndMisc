#!/bin/bash
# Script to check and enable all digital wellbeing services
# Checks: pacman wrapper, midnight shutdown, startup monitor, periodic systems, hosts and hosts guard
#
# Usage:
#   sudo ./check_and_enable_services.sh [options]
# Options:
#   --dry-run    Show what would be done without making changes
#   --status     Only show status, don't enable anything
#   -h|--help    Show help

set -euo pipefail

# Prefix for every absolute path the checks probe. Empty means the real
# filesystem, which is the only value production ever uses; the test harness
# points it at a fixture tree instead. The libs read it via `${SERVICES_ROOT?}`
# with no default, so this assignment is required rather than optional: several
# repairs write outside `run` (chattr, find -delete, an append to
# resolved.conf), and a caller that forgot to set it would edit the real /etc.
export SERVICES_ROOT=""

# Every check lives in a lib beside this file; this script keeps only the
# configuration, argument parsing and the order the checks run in.
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib"
# shellcheck source=lib/services_common.sh
. "$LIB_DIR/services_common.sh"
# shellcheck source=lib/services_wrappers.sh
. "$LIB_DIR/services_wrappers.sh"
# shellcheck source=lib/services_units.sh
. "$LIB_DIR/services_units.sh"
# shellcheck source=lib/services_hosts.sh
. "$LIB_DIR/services_hosts.sh"
# shellcheck source=lib/services_hosts_fix.sh
. "$LIB_DIR/services_hosts_fix.sh"
# shellcheck source=lib/services_apps.sh
. "$LIB_DIR/services_apps.sh"
# shellcheck source=lib/services_browser.sh
. "$LIB_DIR/services_browser.sh"
# shellcheck source=lib/services_report.sh
. "$LIB_DIR/services_report.sh"

######################################################################
# Configuration
######################################################################
DRY_RUN=0
STATUS_ONLY=0

# Colors
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
NC=$'\033[0m' # No Color

# Get script and config directories
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
CONFIG_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Script paths
PACMAN_WRAPPER_INSTALL="$CONFIG_DIR/periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh"
MAKEPKG_WRAPPER_INSTALL="$CONFIG_DIR/periodic_background/digital_wellbeing/pacman/install_makepkg_wrapper.sh"
# Drift manifests written by the two installers above (see deployment_drift).
PACMAN_WRAPPER_MANIFEST="/var/lib/pacman-wrapper/source.sha256"
MAKEPKG_WRAPPER_MANIFEST="/var/lib/pacman-wrapper/makepkg-source.sha256"
MIDNIGHT_SHUTDOWN_SCRIPT="$CONFIG_DIR/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh"
STARTUP_MONITOR_SCRIPT="$CONFIG_DIR/periodic_background/digital_wellbeing/setup_pc_startup_monitor.sh"
PERIODIC_SYSTEM_SCRIPT="$CONFIG_DIR/periodic_background/setup_periodic_system.sh"
HOSTS_INSTALL_SCRIPT="$CONFIG_DIR/periodic_background/hosts/install.sh"
GUARD_LIB_MIGRATE_SCRIPT="$CONFIG_DIR/./fixes/migrate_hosts_guard_to_guard_lib.sh"
COMPULSIVE_BLOCK_SCRIPT="$CONFIG_DIR/periodic_background/digital_wellbeing/block_compulsive_opening.sh"
LEECHBLOCK_SCRIPT="$CONFIG_DIR/periodic_background/digital_wellbeing/install_leechblock.sh"
REMOVE_GUEST_MODE_SCRIPT="$CONFIG_DIR/periodic_background/digital_wellbeing/remove_guest_mode.sh"
VBOX_HOSTS_SCRIPT="$CONFIG_DIR/periodic_background/digital_wellbeing/virtualbox/enforce_vbox_hosts.sh"
# screen-locker was EXTRACTED out of this monorepo into its own repo
# (github.com/kuhyx/screen-locker, checked out at ~/screen-locker), so these
# paths deliberately live outside testsAndMisc. They used to point at
# python_pkg/screen_locker/, which stopped existing at extraction time — the
# result was check_workout_locker reporting a red "error" for a service that was
# installed and enabled the whole time, while its "fix" silently did nothing.
# Resolve the invoking user's home: this script re-execs itself via sudo, so
# $HOME would be /root here.
REAL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
REAL_HOME="$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)"
[[ -n $REAL_HOME ]] || REAL_HOME="/home/$REAL_USER"
WORKOUT_LOCKER_REPO="$REAL_HOME/screen-locker"
WORKOUT_LOCKER_INSTALL_SCRIPT="$WORKOUT_LOCKER_REPO/install_systemd.sh"
WORKOUT_LOCKER_SCRIPT="$WORKOUT_LOCKER_REPO/screen_locker/screen_lock.py"

# A MISSING repair script means THIS TOOL is broken: it silently stops repairing
# the thing it exists to repair. That is exactly how the 2026-05-15 reorg left a
# stale $CONFIG_DIR/hosts path here — check_hosts detected the disabled guards
# every run, failed to find setup_hosts_guard.sh, printed one line among a
# hundred, and still exited 0. Five months of dead self-repair, zero symptoms.
# So: record it, log at journal ERROR priority, and exit non-zero with a banner.
declare -a MISSING_SCRIPTS=()

######################################################################
# Parse arguments
######################################################################
ORIGINAL_ARGS=("$@")
while [[ $# -gt 0 ]]; do
	case "$1" in
	--dry-run)
		DRY_RUN=1
		shift
		;;
	--status)
		STATUS_ONLY=1
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		err "Unknown option: $1"
		usage
		exit 1
		;;
	esac
done

require_root "${ORIGINAL_ARGS[@]}"

######################################################################
# Status tracking
######################################################################
declare -A SERVICE_STATUS
ISSUES_FOUND=0
FIXES_APPLIED=0

######################################################################
# Check functions
######################################################################

######################################################################
# Main
######################################################################
main() {
	echo ""
	echo "Digital Wellbeing Services Status Check"
	echo "========================================"
	echo "Date: $(date)"
	echo "User: ${SUDO_USER:-$USER}"
	if [[ $DRY_RUN -eq 1 ]]; then
		echo "Mode: DRY RUN (no changes will be made)"
	elif [[ $STATUS_ONLY -eq 1 ]]; then
		echo "Mode: STATUS ONLY (no changes will be made)"
	else
		echo "Mode: CHECK AND FIX"
	fi

	check_pacman_wrapper
	check_makepkg_wrapper
	check_midnight_shutdown
	check_startup_monitor
	check_periodic_systems
	check_hosts
	check_compulsive_blocker
	check_leechblock
	check_guest_mode_removal
	check_vbox_hosts
	check_workout_locker

	print_summary
}

main

######################################################################
# A missing repair script means this tool cannot do the one job it exists for.
# Exiting 0 there is indistinguishable from "everything is fine" — which is how
# it hid dead hosts self-repair for five months. Make it impossible to miss.
######################################################################
if [[ ${#MISSING_SCRIPTS[@]} -gt 0 ]]; then
	printf '\n%s' "$RED"
	printf '=%.0s' {1..74}
	printf "\n  SELF-REPAIR IS BROKEN — %d repair script(s) MISSING\n" "${#MISSING_SCRIPTS[@]}"
	printf '=%.0s' {1..74}
	printf '%s\n' "$NC"
	for missing in "${MISSING_SCRIPTS[@]}"; do
		err "$missing"
	done
	printf '%sThe services above are NOT being repaired — this tool found the\n' "$RED"
	printf 'problem and then could not run the fix. Correct these paths first.%s\n' "$NC"
	printf '%sAlso logged at error priority: journalctl -p err -t check-and-enable-services%s\n\n' "$CYAN" "$NC"
	exit 2
fi

exit 0

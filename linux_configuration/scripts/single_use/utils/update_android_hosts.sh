#!/bin/bash
# update_android_hosts.sh - Deploy Android Guardian (hosts blocking + app blocker)
# This creates a persistent protection that can ONLY be controlled via ADB
set -euo pipefail

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"
# shellcheck source=../../lib/android.sh
source "$SCRIPT_DIR/../../lib/android.sh"

GUARDIAN_MODULE_DIR="$SCRIPT_DIR/android_guardian"
GUARDIAN_DATA_DIR="/data/adb/android_guardian"
MODULE_DEST="/data/adb/modules/android_guardian"

# Ensure android-tools (adb) is installed
ensure_adb_installed() {
	if command -v adb &>/dev/null; then
		return 0
	fi

	log "adb not found, installing android-tools..."

	if command -v pacman &>/dev/null; then
		sudo pacman -S --noconfirm android-tools || die "Failed to install android-tools"
	elif command -v apt-get &>/dev/null; then
		# `apt-get update && apt-get install ... || die` would also die when the
		# update succeeded but the install failed to REPORT - and, worse, skipped
		# die entirely if update itself failed. Check each step.
		sudo apt-get update || die "Failed to update apt package lists"
		sudo apt-get install -y adb || die "Failed to install adb"
	elif command -v dnf &>/dev/null; then
		sudo dnf install -y android-tools || die "Failed to install android-tools"
	else
		die "adb not found and could not determine package manager. Please install android-tools manually."
	fi

	# Verify installation
	if ! command -v adb &>/dev/null; then
		die "adb installation failed"
	fi

	log "android-tools installed successfully"
}

show_usage() {
	cat <<EOF
Usage: $(basename "$0") [COMMAND]

Commands:
  install       Install/update Android Guardian module (default)
  status        Show guardian status
  disable       Temporarily disable guardian (requires ADB)
  enable        Re-enable guardian (requires ADB)
  uninstall     Remove guardian module (requires ADB + disable first)
  logs          Show guardian logs
  block-app     Add an app to block list
  unblock-app   Remove an app from block list
  list-blocked  Show blocked apps list

  pair          Pair with device over WiFi (Android 11+, no USB needed)
  connect       Connect to already-paired device over WiFi
  disconnect    Disconnect wireless ADB

Android Guardian provides:
  - Persistent hosts-based ad/tracker blocking
  - Automatic uninstallation of forbidden apps (browsers, food delivery, etc.)
  - Protection that can ONLY be controlled via ADB connection

The module CANNOT be disabled from the Magisk app on the phone.
You MUST connect the phone to a PC and use this script to control it.

Wireless Setup (Android 11+):
  1. On phone: Settings > Developer Options > Wireless debugging > Enable
  2. Tap "Pair device with pairing code" to get IP:port and code
  3. Run: $0 pair
  4. Future connections: $0 connect

EOF
}

# Wireless ADB connection file
WIRELESS_CONFIG="$HOME/.config/android_guardian_wireless"

# shellcheck source=lib/android_device.sh
source "$SCRIPT_DIR/lib/android_device.sh"
# shellcheck source=lib/android_module.sh
source "$SCRIPT_DIR/lib/android_module.sh"
# shellcheck source=lib/android_commands.sh
source "$SCRIPT_DIR/lib/android_commands.sh"


# Main
# Initialize Android script (handles sudo, sets WORK_DIR)
init_android_script "$@"

COMMAND="${1:-install}"
shift || true

case "$COMMAND" in
install)
	cmd_install
	;;
status)
	cmd_status
	;;
disable)
	cmd_disable
	;;
enable)
	cmd_enable
	;;
uninstall)
	cmd_uninstall
	;;
logs)
	cmd_logs
	;;
block-app)
	cmd_block_app "$@"
	;;
unblock-app)
	cmd_unblock_app "$@"
	;;
list-blocked)
	cmd_list_blocked
	;;
pair)
	cmd_pair
	;;
connect)
	cmd_connect
	;;
disconnect)
	cmd_disconnect
	;;
-h | --help | help)
	show_usage
	;;
*)
	echo "Unknown command: $COMMAND"
	show_usage
	exit 1
	;;
esac

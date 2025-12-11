#!/bin/bash
# Shared functions for Android-related scripts
# Source this file after sourcing common.sh

# Prevent multiple sourcing
[[ -n ${_LIB_ANDROID_LOADED:-} ]] && return 0
_LIB_ANDROID_LOADED=1

ANDROID_WORK_DIR="${HOME}/.cache/android-adblock"
ensure_dir "$ANDROID_WORK_DIR"

# Exit with error message
die() {
	echo "[ERROR] $*" >&2
	exit 1
}

# Print section header
print_header() {
	echo
	echo "========================================"
	echo "  $1"
	echo "========================================"
	echo
}

# Initialize an Android script with common setup
# Usage: init_android_script "$@"
# This combines: require_hosts_readable, sets WORK_DIR
init_android_script() {
	require_hosts_readable "$@"
	WORK_DIR="$ANDROID_WORK_DIR"
	export WORK_DIR
}

# Check if ADB device is connected
check_adb_device() {
	log "Checking device connection..."
	if ! adb devices | grep -q "device$"; then
		die "No device connected. Enable USB debugging and connect your phone."
	fi
	log "Device connected"
}

# Check if device has root access
check_adb_root() {
	log "Checking root access..."
	if ! adb shell "su -c 'echo test'" 2>/dev/null | grep -q "test"; then
		die "Root access not available. Make sure Magisk is installed and grant root to Shell."
	fi
	log "Root access confirmed"
}

# Re-exec with sudo if needed to read /etc/hosts
require_hosts_readable() {
	if [[ $EUID -ne 0 ]] && [[ ! -r /etc/hosts ]]; then
		exec sudo -E bash "$0" "$@"
	fi
}

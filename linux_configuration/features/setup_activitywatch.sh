#!/bin/bash
# Script to set up ActivityWatch on Arch Linux with i3
# Handles installation, startup, autostart, and i3blocks status
# Handles sudo privileges automatically

set -e # Exit on any error

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Function to check and request sudo privileges for package installation
check_sudo() {
	if [[ $EUID -ne 0 ]] && [[ $1 == "install" ]]; then
		echo "Package installation requires sudo privileges."
		echo "Requesting sudo access..."
		exec sudo "$0" "$@"
	fi
}

# Get the actual user (even when running with sudo)
set_actual_user_vars

echo "ActivityWatch Setup for Arch Linux + i3"
echo "======================================="
echo "Current Date: $(date)"
echo "User: $ACTUAL_USER"
echo "Target user: $ACTUAL_USER"
echo "User home: $USER_HOME"

# Function to check if ActivityWatch is installed
check_activitywatch_installed() {
	echo ""
	echo "1. Checking ActivityWatch Installation..."
	echo "========================================"

	# Check if activitywatch-bin is installed via pacman
	if pacman -Qi activitywatch-bin &>/dev/null; then
		echo "✓ activitywatch-bin package is installed"
		return 0
	fi

	# Check if aw-qt binary exists in common locations
	local common_paths=(
		"/usr/bin/aw-qt"
		"/usr/local/bin/aw-qt"
		"$USER_HOME/.local/bin/aw-qt"
		"$USER_HOME/activitywatch/aw-qt"
	)

	for path in "${common_paths[@]}"; do
		if [[ -x $path ]]; then
			echo "✓ ActivityWatch found at: $path"
			return 0
		fi
	done

	echo "✗ ActivityWatch not found"
	return 1
}

# shellcheck source=lib/aw_install.sh
source "$SCRIPT_DIR/lib/aw_install.sh"
# shellcheck source=lib/aw_service.sh
source "$SCRIPT_DIR/lib/aw_service.sh"
# shellcheck source=lib/aw_autostart.sh
source "$SCRIPT_DIR/lib/aw_autostart.sh"


# Main execution flow
main() {
	local need_install=false
	local need_start=false

	# Check installation
	if ! check_activitywatch_installed; then
		need_install=true
	fi

	# Install if needed
	if [[ $need_install == true ]]; then
		install_activitywatch
	fi

	# Check if running
	if ! check_activitywatch_running; then
		need_start=true
	fi

	# Start if needed
	if [[ $need_start == true ]]; then
		start_activitywatch
	fi

	# Always set up autostart and i3blocks (in case they're missing)
	setup_autostart
	create_i3blocks_status
	test_setup
	show_instructions
}

# Run main function
main "$@"

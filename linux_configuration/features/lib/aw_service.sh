#!/bin/bash
# Service checks, startup and the autostart unit.
#
# Sourced by setup_activitywatch.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# Function to check if ActivityWatch is running
check_activitywatch_running() {
	echo ""
	echo "3. Checking ActivityWatch Status..."
	echo "=================================="

	# Check for aw-qt process
	if pgrep -f "aw-qt" >/dev/null; then
		echo "✓ ActivityWatch (aw-qt) is running"
		return 0
	fi

	# Check for aw-server process
	if pgrep -f "aw-server" >/dev/null; then
		echo "✓ ActivityWatch server is running"
		return 0
	fi

	echo "✗ ActivityWatch is not running"
	return 1
}

# Function to start ActivityWatch
start_activitywatch() {
	echo ""
	echo "4. Starting ActivityWatch..."
	echo "==========================="

	# Find aw-qt executable
	local aw_qt_path=""

	if command -v aw-qt &>/dev/null; then
		aw_qt_path="$(which aw-qt)"
	elif [[ -x "/usr/bin/aw-qt" ]]; then
		aw_qt_path="/usr/bin/aw-qt"
	else
		echo "✗ Could not find aw-qt executable"
		return 1
	fi

	echo "Starting ActivityWatch as user: $ACTUAL_USER"
	echo "Using aw-qt from: $aw_qt_path"

	# Start as the actual user in the background
	if [[ $EUID -eq 0 ]]; then
		# Running as root, start as user
		sudo -u "$ACTUAL_USER" env DISPLAY=:0 "$aw_qt_path" &
	else
		# Running as user
		"$aw_qt_path" &
	fi

	# Give it time to start
	sleep 3

	if check_activitywatch_running >/dev/null 2>&1; then
		echo "✓ ActivityWatch started successfully"
	else
		echo "! ActivityWatch may be starting (check system tray)"
	fi
}

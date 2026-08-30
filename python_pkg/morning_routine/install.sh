#!/bin/bash
# Install the morning routine: the workout lock, started at the alarm time.
#
# What it does:
#   1. Installs morning-routine.service (user service, started at alarm time).
#   2. Clears the retired standalone wake-alarm.service left by old installs.
#   3. Leaves workout-locker.service + the early-bird timer for login / 08:30.
#
# Prereq: run wake_alarm's own install.sh first (https://github.com/kuhyx/wake-alarm).
# It installs wake-alarm-trigger.timer, which ticks every minute and starts
# this unit at the time the phone synced. The PC no longer wakes anyone, so
# there is no longer a shutdown wrapper or systemd-sleep hook involved.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
SERVICE_SRC="$SCRIPT_DIR/morning-routine.service"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=== Unified Morning Routine Installer ==="

# 1. Install the orchestrator user service.
echo "[1/2] Installing morning-routine.service..."
mkdir -p "$SYSTEMD_USER_DIR"
cp "$SERVICE_SRC" "$SYSTEMD_USER_DIR/morning-routine.service"
systemctl --user daemon-reload
echo "  Installed to $SYSTEMD_USER_DIR/morning-routine.service"

# 2. Clear the retired wake-alarm.service, which no longer exists upstream.
echo "[2/2] Clearing the retired wake-alarm.service..."
if systemctl --user cat wake-alarm.service &>/dev/null; then
	systemctl --user disable wake-alarm.service 2>/dev/null || true
	systemctl --user stop wake-alarm.service 2>/dev/null || true
	echo "  retired wake-alarm.service disabled"
else
	echo "  wake-alarm.service not installed; nothing to clear"
fi

echo "=== Installation complete ==="
echo "wake-alarm-trigger.timer starts this at the phone's synced alarm time."
echo "Test now:"
echo "  python -m python_pkg.morning_routine._orchestrator --production"

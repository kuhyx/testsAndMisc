#!/bin/bash
# Install the unified morning routine: wake alarm -> workout lock as one flow.
#
# What it does:
#   1. Installs morning-routine.service (user service, started on resume).
#   2. Disables the standalone wake-alarm.service autostart: the orchestrator
#      runs the alarm now, and this also removes its evening-login firing quirk.
#   3. Leaves workout-locker.service + the early-bird timer for login / 08:30.
#
# Prereq: run wake_alarm's own install.sh first (https://github.com/kuhyx/wake-alarm) —
# it installs the rtcwake/fan sudoers entries, python-kasa, and the
# systemd-sleep hook that starts morning-routine.service on resume. This
# script does not duplicate that hook install.

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

# 2. Disable the standalone wake-alarm.service autostart (orchestrator owns it).
echo "[2/2] Disabling standalone wake-alarm.service autostart..."
if systemctl --user cat wake-alarm.service &>/dev/null; then
    systemctl --user disable wake-alarm.service 2>/dev/null || true
    systemctl --user stop wake-alarm.service 2>/dev/null || true
    echo "  wake-alarm.service autostart disabled (alarm runs via orchestrator)"
else
    echo "  wake-alarm.service not installed; nothing to disable"
fi

echo "=== Installation complete ==="
echo "On resume the morning routine runs: wake alarm -> workout lock."
echo "Test now:"
echo "  python -m python_pkg.morning_routine._orchestrator --with-alarm --production"

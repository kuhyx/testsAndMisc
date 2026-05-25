#!/bin/bash
# Install the unified morning routine: wake alarm -> workout lock as one flow.
#
# What it does:
#   1. Installs morning-routine.service (user service, started on resume).
#   2. Reinstalls the systemd-sleep hook so resume starts morning-routine
#      (alarm first, then the workout lock - one fullscreen owner at a time).
#   3. Disables the standalone wake-alarm.service autostart: the orchestrator
#      runs the alarm now, and this also removes its evening-login firing quirk.
#   4. Leaves workout-locker.service + the early-bird timer for login / 08:30.
#
# Prereq: run python_pkg/wake_alarm/install.sh first for the rtcwake/fan
# sudoers entries, the fan-control script, and python-kasa.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
REPO_ROOT="$(readlink -f "$SCRIPT_DIR/../..")"
SERVICE_SRC="$SCRIPT_DIR/morning-routine.service"
SLEEP_HOOK_SRC="$REPO_ROOT/python_pkg/wake_alarm/sleep-hook.sh"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SLEEP_HOOK_DST="/usr/lib/systemd/system-sleep/wake-alarm.sh"

echo "=== Unified Morning Routine Installer ==="

# 1. Install the orchestrator user service.
echo "[1/3] Installing morning-routine.service..."
mkdir -p "$SYSTEMD_USER_DIR"
cp "$SERVICE_SRC" "$SYSTEMD_USER_DIR/morning-routine.service"
systemctl --user daemon-reload
echo "  Installed to $SYSTEMD_USER_DIR/morning-routine.service"

# 2. Reinstall the sleep hook (now starts morning-routine.service on resume).
echo "[2/3] Installing systemd-sleep hook (requires sudo)..."
sudo cp "$SLEEP_HOOK_SRC" "$SLEEP_HOOK_DST"
sudo chmod 0755 "$SLEEP_HOOK_DST"
echo "  Installed to $SLEEP_HOOK_DST"

# 3. Disable the standalone wake-alarm.service autostart (orchestrator owns it).
echo "[3/3] Disabling standalone wake-alarm.service autostart..."
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

#!/bin/bash
set -euo pipefail

# Kill any lingering player2 steam processes
pkill -u player2 -f steam 2>/dev/null || true
sleep 0.5

# Allow player2 to use the main X display
xhost +local: > /dev/null

# Launch Steam as player2 on the same X display (:0)
DISPLAY=":0" sudo -H -u player2 steam &

echo "player2 Steam launched. Move the window to your HDMI monitor."

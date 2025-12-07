#!/bin/bash
# YouTube Music Wrapper - Blocks launch when focus apps are running
# This replaces the actual youtube-music binary

set -euo pipefail

REAL_BINARY="/opt/YouTube Music/youtube-music.real"
LOG_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/music-parallelism/music-parallelism.log"

log_message() {
	local msg
	msg="$(date '+%Y-%m-%d %H:%M:%S') - $1"
	echo "$msg" >&2
	echo "$msg" >>"$LOG_FILE" 2>/dev/null || true
}

# Focus apps - window titles to check (only visible windows count)
FOCUS_APPS_WINDOWS=(
	"Visual Studio Code"
	"VSCodium"
	"Cursor"
	"IntelliJ IDEA"
	"PyCharm"
	"WebStorm"
	"CLion"
	"Rider"
	"Sublime Text"
	"Blender"
	"Godot"
	"Unity"
	"Unreal Editor"
)

# Focus apps - process patterns to check
FOCUS_APPS_PROCESSES=(
	"steam_app_"
	"gamescope"
)

# Check if any focus app is running (window-based detection)
is_focus_app_running() {
	# Check windows first
	if command -v xdotool &>/dev/null; then
		for app in "${FOCUS_APPS_WINDOWS[@]}"; do
			if xdotool search --name "$app" &>/dev/null 2>&1; then
				echo "$app"
				return 0
			fi
		done
	fi

	# Check specific processes
	for app in "${FOCUS_APPS_PROCESSES[@]}"; do
		if pgrep -f "$app" &>/dev/null; then
			echo "$app"
			return 0
		fi
	done

	return 1
}

# Main
if focus_app=$(is_focus_app_running); then
	log_message "BLOCKED: YouTube Music launch prevented (focus app: $focus_app)"
	notify-send -u normal -t 3000 "🚫 YouTube Music Blocked" "Focus mode active ($focus_app)" 2>/dev/null || true
	exit 1
fi

# No focus app running, launch normally
exec "$REAL_BINARY" "$@"

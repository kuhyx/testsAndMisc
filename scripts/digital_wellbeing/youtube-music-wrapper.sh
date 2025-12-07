#!/bin/bash
# YouTube Music Wrapper - Blocks launch when focus apps are running
# This replaces the actual youtube-music binary

set -euo pipefail

REAL_BINARY="/opt/YouTube Music/youtube-music"
LOG_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/music-parallelism/music-parallelism.log"

log_message() {
	local msg
	msg="$(date '+%Y-%m-%d %H:%M:%S') - $1"
	echo "$msg" >&2
	echo "$msg" >>"$LOG_FILE" 2>/dev/null || true
}

# Focus apps that block music
FOCUS_APPS=(
	"code" "Code" "vscodium" "cursor"
	"jetbrains" "idea" "pycharm" "webstorm" "clion" "rider"
	"sublime_text" "atom" "neovide"
	"steam_app" "steamwebhelper" "gamescope"
	"blender" "godot" "unity" "UnrealEditor"
)

# Check if any focus app is running
is_focus_app_running() {
	for app in "${FOCUS_APPS[@]}"; do
		if pgrep -i -f "$app" &>/dev/null; then
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

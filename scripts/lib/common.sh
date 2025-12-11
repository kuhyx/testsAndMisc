#!/bin/bash
# Common library functions for linux-configuration scripts
# Source this file at the beginning of scripts that need shared functionality
#
# Usage: source "$(dirname "$(readlink -f "$0")")/../lib/common.sh"
# Or:    source "/path/to/scripts/lib/common.sh"

# Prevent multiple sourcing
[[ -n ${_LIB_COMMON_LOADED:-} ]] && return 0
_LIB_COMMON_LOADED=1

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

# Log message with timestamp to stderr and optionally to a file
# Usage: log_message "message" [log_file]
log_message() {
	local msg="$1"
	local log_file="${2:-}"
	local formatted
	formatted="$(date '+%Y-%m-%d %H:%M:%S') - $msg"
	echo "$formatted" >&2
	if [[ -n "$log_file" ]]; then
		echo "$formatted" >>"$log_file" 2>/dev/null || true
	fi
}

# Simple log with timestamp (no file output)
# Usage: log "message"
log() {
	printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

# =============================================================================
# SUDO / ROOT HANDLING
# =============================================================================

# Check if running as root, if not re-exec with sudo
# Usage: require_root "$@"
require_root() {
	if [[ $EUID -ne 0 ]]; then
		echo "This script requires root privileges."
		echo "Requesting sudo access..."
		exec sudo "$0" "$@"
	fi
}

# Get the actual user even when running with sudo
# Usage: ACTUAL_USER=$(get_actual_user)
get_actual_user() {
	echo "${SUDO_USER:-$USER}"
}

# Get the actual user's home directory
# Usage: USER_HOME=$(get_actual_user_home)
get_actual_user_home() {
	local user
	user=$(get_actual_user)
	if [[ "$user" == "root" ]]; then
		echo "/root"
	else
		echo "/home/$user"
	fi
}

# =============================================================================
# ARGUMENT PARSING HELPERS
# =============================================================================

# Parse common --interactive/-i and --help/-h flags
# Sets INTERACTIVE_MODE variable (exported for use by calling scripts)
# Usage: parse_common_args "$@"
#        shift "$COMMON_ARGS_SHIFT"
export INTERACTIVE_MODE=false
export COMMON_ARGS_SHIFT=0

parse_interactive_args() {
	INTERACTIVE_MODE=false
	COMMON_ARGS_SHIFT=0
	local script_name="${0##*/}"

	while [[ $# -gt 0 ]]; do
		case $1 in
		-i | --interactive)
			INTERACTIVE_MODE=true
			((COMMON_ARGS_SHIFT++))
			shift
			;;
		-h | --help)
			echo "Usage: $script_name [OPTIONS]"
			echo "Options:"
			echo "  -i, --interactive    Enable interactive prompts (default: auto-yes)"
			echo "  -h, --help          Show this help message"
			exit 0
			;;
		*)
			# Stop parsing at first unknown argument
			break
			;;
		esac
	done
}

# =============================================================================
# FOCUS APP DETECTION (for digital wellbeing scripts)
# =============================================================================

# Default focus apps - can be overridden before calling is_focus_app_running
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

FOCUS_APPS_PROCESSES=(
	"steam_app_"
	"gamescope"
)

# Check if any focus app is running (window-based detection)
# Returns 0 if focus app found, 1 otherwise
# Echoes the name of the found app
is_focus_app_running() {
	# Check windows first
	if command -v xdotool &>/dev/null; then
		local app
		for app in "${FOCUS_APPS_WINDOWS[@]}"; do
			if xdotool search --name "$app" &>/dev/null 2>&1; then
				echo "$app"
				return 0
			fi
		done
	fi

	# Check specific processes
	local app
	for app in "${FOCUS_APPS_PROCESSES[@]}"; do
		if pgrep -f "$app" &>/dev/null; then
			echo "$app"
			return 0
		fi
	done

	return 1
}

# =============================================================================
# COMMAND AVAILABILITY
# =============================================================================

# Check if a command exists
# Usage: if require_command ffmpeg; then ...
require_command() {
	local cmd="$1"
	local pkg="${2:-$1}"
	if ! command -v "$cmd" >/dev/null 2>&1; then
		echo "Error: '$cmd' is not installed or not in PATH." >&2
		echo "Install with: sudo pacman -S $pkg" >&2
		return 1
	fi
	return 0
}

# =============================================================================
# NOTIFICATION
# =============================================================================

# Send desktop notification (fails silently if notify-send not available)
# Usage: notify "Title" "Message" [urgency: low/normal/critical] [timeout_ms]
notify() {
	local title="$1"
	local message="$2"
	local urgency="${3:-normal}"
	local timeout="${4:-5000}"

	if command -v notify-send &>/dev/null; then
		notify-send -u "$urgency" -t "$timeout" "$title" "$message" 2>/dev/null || true
	fi
}

# =============================================================================
# FILE/PATH UTILITIES
# =============================================================================

# Get the directory containing the calling script
# Usage: SCRIPT_DIR=$(get_script_dir)
get_script_dir() {
	dirname "$(readlink -f "${BASH_SOURCE[1]:-$0}")"
}

# Ensure a directory exists
# Usage: ensure_dir "/path/to/dir"
ensure_dir() {
	local dir="$1"
	if [[ ! -d "$dir" ]]; then
		mkdir -p "$dir"
	fi
}

# =============================================================================
# SYSTEMD HELPERS
# =============================================================================

# Enable and start a systemd service (user or system)
# Usage: enable_service "service-name" [--user]
enable_service() {
	local service="$1"
	local user_flag="${2:-}"

	if [[ "$user_flag" == "--user" ]]; then
		systemctl --user daemon-reload
		systemctl --user enable --now "$service"
	else
		systemctl daemon-reload
		systemctl enable --now "$service"
	fi
}

# Check if a systemd service is active
# Usage: if is_service_active "service-name" [--user]; then ...
is_service_active() {
	local service="$1"
	local user_flag="${2:-}"

	if [[ "$user_flag" == "--user" ]]; then
		systemctl --user is-active --quiet "$service"
	else
		systemctl is-active --quiet "$service"
	fi
}

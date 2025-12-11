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
	if [[ -n $log_file ]]; then
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
	if [[ $user == "root" ]]; then
		echo "/root"
	else
		echo "/home/$user"
	fi
}

# Set both ACTUAL_USER and USER_HOME variables (common pattern)
# Usage: set_actual_user_vars
#        echo "$ACTUAL_USER"   # => the actual user
#        echo "$USER_HOME"     # => /home/username
set_actual_user_vars() {
	ACTUAL_USER=$(get_actual_user)
	USER_HOME=$(get_actual_user_home)
	export ACTUAL_USER USER_HOME
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

# Handle common argument patterns for scripts with custom usage functions
# Usage: handle_arg_help_or_unknown "$1" usage_function err_function
# Returns: 0 if argument was handled (caller should continue), 1 if not our concern
# Exits: on -h/--help (exit 0) or unknown arg starting with - (exit 2)
handle_arg_help_or_unknown() {
	local arg="$1"
	local usage_fn="${2:-usage}"
	local err_fn="${3:-err}"

	case "$arg" in
	-h | --help)
		"$usage_fn"
		exit 0
		;;
	-*)
		"$err_fn" "Unknown argument: $arg"
		"$usage_fn"
		exit 2
		;;
	*)
		return 1 # Not a flag, let caller handle it
		;;
	esac
	return 0
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

# Check for ImageMagick and display helpful installation message
# Usage: require_imagemagick [optional: "magick" or "convert"]
# Returns: Sets MAGICK_CMD variable to available command
require_imagemagick() {
	local preferred="${1:-}"

	if [[ $preferred == "magick" ]] || [[ -z $preferred ]]; then
		if command -v magick &>/dev/null; then
			MAGICK_CMD="magick"
			export MAGICK_CMD
			return 0
		fi
	fi

	if [[ $preferred == "convert" ]] || [[ -z $preferred ]]; then
		if command -v convert &>/dev/null; then
			MAGICK_CMD="convert"
			export MAGICK_CMD
			return 0
		fi
	fi

	echo "Error: ImageMagick is not installed." >&2
	echo "Install it with:" >&2
	echo "  Arch Linux: sudo pacman -S imagemagick" >&2
	echo "  Ubuntu/Debian: sudo apt install imagemagick" >&2
	return 1
}

# Install missing pacman packages
# Usage: install_missing_pacman_packages pkg1 pkg2 pkg3 ...
# Returns 0 if all packages installed successfully, 1 otherwise
install_missing_pacman_packages() {
	local packages=("$@")
	local missing=()

	for pkg in "${packages[@]}"; do
		if ! pacman -Qi "$pkg" >/dev/null 2>&1; then
			missing+=("$pkg")
		fi
	done

	if [[ ${#missing[@]} -eq 0 ]]; then
		echo "[INFO] All required packages are already installed."
		return 0
	fi

	echo "[INFO] Installing missing packages: ${missing[*]}"
	if ! sudo pacman -S --needed --noconfirm "${missing[@]}"; then
		echo "[ERROR] Failed to install packages" >&2
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
	if [[ ! -d $dir ]]; then
		mkdir -p "$dir"
	fi
}

# =============================================================================
# SYSTEMD HELPERS
# =============================================================================

# Internal helper for running systemctl with optional --user flag
_systemctl_cmd() {
	local user_flag="$1"
	shift
	if [[ $user_flag == "--user" ]]; then
		systemctl --user "$@"
	else
		systemctl "$@"
	fi
}

# Enable and start a systemd service (user or system)
# Usage: enable_service "service-name" [--user]
enable_service() {
	local service="$1"
	local user_flag="${2:-}"
	_systemctl_cmd "$user_flag" daemon-reload
	_systemctl_cmd "$user_flag" enable --now "$service"
}

# Check if a systemd service is active
# Usage: if is_service_active "service-name" [--user]; then ...
is_service_active() {
	_systemctl_cmd "${2:-}" is-active --quiet "$1"
}

# Check if a systemd service is enabled
# Usage: if is_service_enabled "service-name" [--user]; then ...
is_service_enabled() {
	_systemctl_cmd "${2:-}" is-enabled --quiet "$1" 2>/dev/null
}

# =============================================================================
# COLORED LOGGING (for scripts that need colored output)
# =============================================================================

# ANSI color codes
declare -g COLOR_RED='\033[1;31m'
declare -g COLOR_GREEN='\033[1;32m'
declare -g COLOR_YELLOW='\033[1;33m'
declare -g COLOR_BLUE='\033[1;34m'
declare -g COLOR_NC='\033[0m'

log_info() {
	printf "${COLOR_BLUE}[INFO]${COLOR_NC} %s\n" "$*"
}

log_ok() {
	printf "${COLOR_GREEN}[ OK ]${COLOR_NC} %s\n" "$*"
}

log_warn() {
	printf "${COLOR_YELLOW}[WARN]${COLOR_NC} %s\n" "$*" >&2
}

log_error() {
	printf "${COLOR_RED}[ERROR]${COLOR_NC} %s\n" "$*" >&2
}

# Alias for compatibility
warn() { log_warn "$@"; }
err() { log_error "$@"; }

# =============================================================================
# INTERACTIVE PROMPTS
# =============================================================================

# Ask yes/no question, returns 0 for yes, 1 for no
# Usage: if ask_yes_no "Continue?"; then ...
ask_yes_no() {
	local prompt="$1"
	local ans
	read -r -p "$prompt [y/N]: " ans || true
	case "${ans:-}" in
	y | Y | yes | YES) return 0 ;;
	*) return 1 ;;
	esac
}

# Check if a command is available
# Usage: if has_cmd git; then ...
has_cmd() {
	command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# STANDARD SETUP HEADER
# =============================================================================

# Print a standard setup header for scripts
# Usage: print_setup_header "Script Name"
print_setup_header() {
	local title="$1"
	echo "$title"
	printf '=%.0s' $(seq 1 ${#title})
	echo ""
	echo "Current Date: $(date)"
	echo "User: $USER"
	echo "Original user: $(get_actual_user)"
	if [[ $INTERACTIVE_MODE == "true" ]]; then
		echo "Mode: Interactive (prompts enabled)"
	else
		echo "Mode: Automatic (auto-yes, use --interactive for prompts)"
	fi
}

# =============================================================================
# MOUNT/UNMOUNT HELPERS (for hosts guard and similar)
# =============================================================================

# Count mount layers for a path
# Usage: count=$(mount_layers_count "/etc/hosts")
mount_layers_count() {
	local target="$1"
	awk -v t="$target" '$5==t{c++} END{print c+0}' /proc/self/mountinfo 2>/dev/null || echo 0
}

# Collapse all bind mount layers for a path
# Usage: collapse_mounts "/etc/hosts" [max_iterations]
collapse_mounts() {
	local target="$1"
	local max_iter="${2:-20}"
	local i=0

	if has_cmd mountpoint; then
		while mountpoint -q "$target"; do
			umount -l "$target" >/dev/null 2>&1 || break
			i=$((i + 1))
			((i >= max_iter)) && break
		done
	else
		local cnt
		cnt=$(mount_layers_count "$target")
		while ((cnt > 1)); do
			umount -l "$target" >/dev/null 2>&1 || break
			i=$((i + 1))
			((i >= max_iter)) && break
			cnt=$(mount_layers_count "$target")
		done
	fi
}

# =============================================================================
# RESOLUTION/FORMAT VALIDATION
# =============================================================================

# Validate resolution format (WIDTHxHEIGHT)
# Usage: if validate_resolution "1920x1080"; then ...
validate_resolution() {
	local res="$1"
	[[ $res =~ ^[0-9]+x[0-9]+$ ]]
}

# Generate output filename with suffix
# Usage: output=$(generate_output_filename "input.jpg" "_resized")
generate_output_filename() {
	local input="$1"
	local suffix="$2"
	local ext="${3:-}"

	local basename dirname filename extension
	basename=$(basename "$input")
	dirname=$(dirname "$input")
	filename="${basename%.*}"
	extension="${basename##*.}"

	# Handle files without extension
	if [[ $filename == "$extension" ]]; then
		extension="${ext:-jpg}"
	fi

	echo "${dirname}/${filename}${suffix}.${extension}"
}

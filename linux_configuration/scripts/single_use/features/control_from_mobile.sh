#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/control-from-mobile"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/control-from-mobile"
PASSWORD_FILE="$CONFIG_DIR/vnc.pass"
ENV_FILE="$CONFIG_DIR/env"
RUNNER_FILE="$CONFIG_DIR/start-x11vnc.sh"
SERVICE_NAME="control-from-mobile.service"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SYSTEMD_USER_DIR/$SERVICE_NAME"
DEFAULT_DISPLAY="${DISPLAY:-:0}"
DEFAULT_PORT=5901
DEFAULT_BIND_ADDR="0.0.0.0"
readonly SCRIPT_NAME CONFIG_DIR STATE_DIR PASSWORD_FILE ENV_FILE RUNNER_FILE SERVICE_NAME SYSTEMD_USER_DIR SERVICE_FILE DEFAULT_DISPLAY DEFAULT_PORT DEFAULT_BIND_ADDR

usage() {
  cat << 'EOF'
Usage: control_from_mobile.sh <command> [options]

Commands:
	setup [--force-password]  Install dependencies, create configs, and write the systemd user service.
	start                     Start the VNC bridge (via systemd user unit when available).
	stop                      Stop the bridge.
	restart                   Restart the bridge.
	status                    Show whether the bridge service is running.
	enable                    Enable the service so it starts after login.
	disable                   Disable automatic start after login.
	info                      Show connection details and Android app suggestions.
	uninstall                 Stop the service and remove generated files (keeps password unless --purge).
	help                      Show this message.

Options:
	--force-password          Regenerate the VNC password during setup.
	--purge                   Delete the stored VNC password during uninstall.

Examples:
	./control_from_mobile.sh setup
	./control_from_mobile.sh start
	./control_from_mobile.sh info

EOF
}

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*"
}

warn() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

die() {
  warn "$*"
  exit 1
}

require_non_root() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    die "Run this script as a regular desktop user, not root."
  fi
}

prompt_yes_no() {
  local prompt="$1"
  local reply
  read -r -p "$prompt [y/N]: " reply
  case "$reply" in
    [Yy][Ee][Ss] | [Yy]) return 0 ;;
    *) return 1 ;;
  esac
}

ensure_directories() {
  mkdir -p "$CONFIG_DIR" "$STATE_DIR" "$SYSTEMD_USER_DIR"
  chmod 700 "$CONFIG_DIR"
}

missing_commands() {
  local missing=()
  for cmd in "$@"; do
    if ! command -v "$cmd" > /dev/null 2>&1; then
      missing+=("$cmd")
    fi
  done
  printf '%s\n' "${missing[@]-}"
}

install_dependencies() {
  if ! command -v systemctl > /dev/null 2>&1; then
    die "systemctl not found. Install systemd before running this script."
  fi

  local required=(x11vnc qrencode ssh)
  local needed=()
  mapfile -t needed < <(missing_commands "${required[@]}")
  if ((${#needed[@]} == 0)); then
    log "All required packages (${required[*]}) are present."
    return
  fi

  if command -v pacman > /dev/null 2>&1; then
    log "Installing missing packages: ${needed[*]}"
    sudo pacman -S --needed --noconfirm "${needed[@]}"
  else
    die "Missing commands (${needed[*]}). Install them manually and rerun setup."
  fi
}

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/mobile_service.sh
source "$SCRIPT_DIR/lib/mobile_service.sh"

main() {
  require_non_root

  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    setup)
      local force=0
      if [[ ${1:-} == "--force-password" ]]; then
        force=1
        shift || true
      fi
      ensure_directories
      install_dependencies
      create_password_file "$force"
      create_env_file
      create_runner_script
      create_service_file
      reload_user_daemon
      log "Setup complete. Start the service with: $SCRIPT_NAME start"
      ;;
    start)
      start_service
      show_info
      ;;
    stop)
      stop_service
      ;;
    restart)
      stop_service
      start_service
      ;;
    status)
      status_service
      ;;
    enable)
      enable_service
      ;;
    disable)
      disable_service
      ;;
    info)
      show_info
      ;;
    uninstall)
      local purge=0
      if [[ ${1:-} == "--purge" ]]; then
        purge=1
        shift || true
      fi
      uninstall_files "$purge"
      ;;
    help | --help | -h | "")
      usage
      ;;
    *)
      usage
      die "Unknown command: $cmd"
      ;;
  esac
}

main "$@"

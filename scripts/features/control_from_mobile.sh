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
	cat <<'EOF'
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
	if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
		die "Run this script as a regular desktop user, not root."
	fi
}

prompt_yes_no() {
	local prompt="$1"
	local reply
	read -r -p "$prompt [y/N]: " reply
	case "$reply" in
		[Yy][Ee][Ss]|[Yy]) return 0 ;;
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
		if ! command -v "$cmd" >/dev/null 2>&1; then
			missing+=("$cmd")
		fi
	done
	printf '%s\n' "${missing[@]-}"
}

install_dependencies() {
	if ! command -v systemctl >/dev/null 2>&1; then
		die "systemctl not found. Install systemd before running this script."
	fi

	local required=(x11vnc qrencode ssh)
	local needed=()
	mapfile -t needed < <(missing_commands "${required[@]}")
	if (( ${#needed[@]} == 0 )); then
		log "All required packages (${required[*]}) are present."
		return
	fi

	if command -v pacman >/dev/null 2>&1; then
		log "Installing missing packages: ${needed[*]}"
		sudo pacman -S --needed --noconfirm "${needed[@]}"
	else
		die "Missing commands (${needed[*]}). Install them manually and rerun setup."
	fi
}

create_password_file() {
	local force=${1:-0}
		if [[ -f "$PASSWORD_FILE" && "$force" -ne 1 ]];
		then
			log "Using existing VNC password file at $PASSWORD_FILE"
			return
		fi

		if [[ -f "$PASSWORD_FILE" ]]; then
			if ! prompt_yes_no "Regenerate the stored VNC password?"; then
				log "Keeping existing password."
				return
			fi
		fi

	local password confirm generated=0
	read -rsp "Enter VNC password (leave blank to auto-generate): " password
	printf '\n'
	if [[ -z "$password" ]]; then
		generated=1
		password=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 8)
		log "Generated VNC password: $password"
	else
		read -rsp "Confirm password: " confirm
		printf '\n'
		if [[ "$password" != "$confirm" ]]; then
			die "Passwords do not match."
		fi
	fi

	local tmp
	tmp=$(mktemp)
	x11vnc -storepasswd "$password" "$tmp" >/dev/null
	install -m 600 "$tmp" "$PASSWORD_FILE"
	rm -f "$tmp"

	if (( generated == 0 )); then
		log "Password stored securely at $PASSWORD_FILE (hashed)."
	else
		log "Please write down the generated password; it will be needed on your Android device."
	fi
}

create_env_file() {
	if [[ -f "$ENV_FILE" ]]; then
		return
	fi
	cat >"$ENV_FILE" <<EOF
# control-from-mobile configuration
# Adjust these values if needed and rerun: systemctl --user restart $SERVICE_NAME
X11_DISPLAY="$DEFAULT_DISPLAY"
VNC_PORT="$DEFAULT_PORT"
# Use 127.0.0.1 to force SSH tunnel-only access, or 0.0.0.0 to expose on LAN.
VNC_BIND_ADDR="$DEFAULT_BIND_ADDR"
EOF
	chmod 600 "$ENV_FILE"
}

create_runner_script() {
	cat >"$RUNNER_FILE" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

CONFIG_DIR="$(dirname "$(readlink -f "$0")")"
PASSWORD_FILE="$CONFIG_DIR/vnc.pass"
ENV_FILE="$CONFIG_DIR/env"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/control-from-mobile"
mkdir -p "$STATE_DIR"

if [[ ! -f "$PASSWORD_FILE" ]]; then
	echo "Missing VNC password file at $PASSWORD_FILE" >&2
	exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
	# shellcheck disable=SC1090
	source "$ENV_FILE"
fi

X11_DISPLAY="${X11_DISPLAY:-${DISPLAY:-:0}}"
VNC_PORT="${VNC_PORT:-5901}"
VNC_BIND_ADDR="${VNC_BIND_ADDR:-0.0.0.0}"

LOG_FILE="$STATE_DIR/x11vnc.log"
exec /usr/bin/x11vnc \
	-display "$X11_DISPLAY" \
	-rfbport "$VNC_PORT" \
	-listen "$VNC_BIND_ADDR" \
	-forever \
	-shared \
	-auth guess \
	-rfbauth "$PASSWORD_FILE" \
	-noxdamage \
	-repeat \
	-ncache 10 \
	-ncache_cr \
	-o "$LOG_FILE"
EOF
	chmod 700 "$RUNNER_FILE"
}

create_service_file() {
	cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=Expose X11 desktop over VNC for Android control
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
EnvironmentFile=$ENV_FILE
ExecStart=$RUNNER_FILE
Restart=on-failure
RestartSec=2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF
}

reload_user_daemon() {
	systemctl --user daemon-reload
}

ensure_service_present() {
	if [[ ! -f "$SERVICE_FILE" || ! -x "$RUNNER_FILE" ]]; then
		die "Service files missing. Run: $SCRIPT_NAME setup"
	fi
}

start_service() {
	ensure_service_present
	systemctl --user start "$SERVICE_NAME"
}

stop_service() {
	systemctl --user stop "$SERVICE_NAME" || true
}

status_service() {
	if systemctl --user is-active --quiet "$SERVICE_NAME"; then
		log "Service is active."
	else
		log "Service is inactive."
	fi
	systemctl --user status "$SERVICE_NAME" --no-pager || true
}

enable_service() {
	ensure_service_present
	systemctl --user enable "$SERVICE_NAME"
}

disable_service() {
	systemctl --user disable "$SERVICE_NAME" || true
}

show_info() {
	ensure_service_present
	# shellcheck disable=SC1090
	[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
	local port="${VNC_PORT:-$DEFAULT_PORT}"
	local bind_addr="${VNC_BIND_ADDR:-$DEFAULT_BIND_ADDR}"
	local display="${X11_DISPLAY:-$DEFAULT_DISPLAY}"

	local is_active="inactive"
	if systemctl --user is-active --quiet "$SERVICE_NAME"; then
		is_active="active"
	fi

	log "Service status: $is_active"
	log "Display: $display"
	log "Listening address: $bind_addr"
	log "VNC port: $port"
	log "Password file: $PASSWORD_FILE"

	local -a ip_list=()
	if command -v hostname >/dev/null 2>&1; then
		while IFS= read -r line; do
			[[ -z "$line" ]] && continue
			ip_list+=("$line")
		done < <(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]' || true)
	fi

	if (( ${#ip_list[@]} > 0 )); then
		log "Detected LAN IPs:"
		for ip in "${ip_list[@]}"; do
			printf '  - %s\n' "$ip"
		done
	else
		warn "Could not detect LAN IPs."
	fi

	printf '\nRecommended Android clients (FOSS):\n'
	printf '  • bVNC (available on F-Droid) — supports full control.\n'
	printf '  • Termux + OpenSSH for establishing an SSH tunnel when exposing only on 127.0.0.1.\n'
	printf '\nConnect via VNC:\n'
	printf '  Host: <your-ip>\n  Port: %s\n  Password: <stored during setup>\n' "$port"

	local qr_host
	if (( ${#ip_list[@]} > 0 )); then
		qr_host="${ip_list[0]}"
	else
		qr_host="$bind_addr"
		if [[ "$qr_host" == "0.0.0.0" || "$qr_host" == "::" ]]; then
			qr_host="127.0.0.1"
		fi
		warn "Using fallback host $qr_host for QR code; replace with an accessible IP if needed."
	fi

	if command -v qrencode >/dev/null 2>&1; then
		printf '\nConnection QR (vnc://%s:%s):\n' "$qr_host" "$port"
		qrencode -o - "vnc://$qr_host:$port" -t ASCII || true
	else
		warn "qrencode not found; reinstall qrencode to get QR codes."
	fi

	printf '\nFor encrypted access outside your LAN, use Termux on Android:\n'
	printf '  ssh -L %s:localhost:%s <user>@<public-ip>\n' "$port" "$port"
	printf 'Then point bVNC to 127.0.0.1:%s.\n' "$port"
}

uninstall_files() {
	local purge_password=${1:-0}
	stop_service
	disable_service
	rm -f "$SERVICE_FILE"
	rm -f "$RUNNER_FILE"
	rm -f "$ENV_FILE"
	if (( purge_password )); then
		rm -f "$PASSWORD_FILE"
		log "Removed password file."
	fi
	reload_user_daemon
	log "Removed generated files."
}

main() {
	require_non_root

	local cmd="${1:-}"
	shift || true

	case "$cmd" in
		setup)
			local force=0
			if [[ "${1:-}" == "--force-password" ]]; then
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
			if [[ "${1:-}" == "--purge" ]]; then
				purge=1
				shift || true
			fi
			uninstall_files "$purge"
			;;
		help|--help|-h|"" )
			usage
			;;
		*)
			usage
			die "Unknown command: $cmd"
			;;
	esac
}

main "$@"

#!/bin/bash
# Credential, env, runner and systemd unit generation.
#
# Sourced by control_from_mobile.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

create_password_file() {
  local force=${1:-0}
  if [[ -f $PASSWORD_FILE && $force -ne 1 ]]; then
    log "Using existing VNC password file at $PASSWORD_FILE"
    return
  fi

  if [[ -f $PASSWORD_FILE ]]; then
    if ! prompt_yes_no "Regenerate the stored VNC password?"; then
      log "Keeping existing password."
      return
    fi
  fi

  local password confirm generated=0
  read -rsp "Enter VNC password (leave blank to auto-generate): " password
  printf '\n'
  if [[ -z $password ]]; then
    generated=1
    password=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 8)
    log "Generated VNC password: $password"
  else
    read -rsp "Confirm password: " confirm
    printf '\n'
    if [[ $password != "$confirm" ]]; then
      die "Passwords do not match."
    fi
  fi

  local tmp
  tmp=$(mktemp)
  x11vnc -storepasswd "$password" "$tmp" > /dev/null
  install -m 600 "$tmp" "$PASSWORD_FILE"
  rm -f "$tmp"

  if ((generated == 0)); then
    log "Password stored securely at $PASSWORD_FILE (hashed)."
  else
    log "Please write down the generated password; it will be needed on your Android device."
  fi
}

create_env_file() {
  if [[ -f $ENV_FILE ]]; then
    return
  fi
  cat > "$ENV_FILE" << EOF
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
  cat > "$RUNNER_FILE" << 'EOF'
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
  cat > "$SERVICE_FILE" << EOF
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
  if [[ ! -f $SERVICE_FILE || ! -x $RUNNER_FILE ]]; then
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
  [[ -f $ENV_FILE ]] && source "$ENV_FILE"
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
  if command -v hostname > /dev/null 2>&1; then
    while IFS= read -r line; do
      [[ -z $line ]] && continue
      ip_list+=("$line")
    done < <(hostname -I 2> /dev/null | tr ' ' '\n' | grep -E '^[0-9]' || true)
  fi

  if ((${#ip_list[@]} > 0)); then
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
  if ((${#ip_list[@]} > 0)); then
    qr_host="${ip_list[0]}"
  else
    qr_host="$bind_addr"
    if [[ $qr_host == "0.0.0.0" || $qr_host == "::" ]]; then
      qr_host="127.0.0.1"
    fi
    warn "Using fallback host $qr_host for QR code; replace with an accessible IP if needed."
  fi

  if command -v qrencode > /dev/null 2>&1; then
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
  if ((purge_password)); then
    rm -f "$PASSWORD_FILE"
    log "Removed password file."
  fi
  reload_user_daemon
  log "Removed generated files."
}

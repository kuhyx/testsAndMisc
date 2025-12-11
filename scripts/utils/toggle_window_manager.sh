#!/bin/bash

set -euo pipefail

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Configuration -----------------------------------------------------------------
TARGET_SESSION_NAME="Xfce Session"
TARGET_PACKAGES=(
	xfwm4          # Compositing window manager with XFCE integration
	xfce4-session  # Provides the Xfce session entry for display managers
	xfce4-panel    # Panel with system tray support
	xfce4-settings # Settings daemon (enables compositing toggle, theming, etc.)
	xfce4-terminal # Handy default terminal for the new environment
)

# Utility functions --------------------------------------------------------------
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }
error() {
	echo "[ERROR] $*" >&2
	exit 1
}

ensure_pacman() {
	require_command pacman "pacman" || error "Required command 'pacman' not found."
	if ! grep -qi "arch" /etc/os-release 2>/dev/null; then
		warn "This script was designed for Arch Linux; continuing anyway."
	fi
}

install_packages() {
	install_missing_pacman_packages "${TARGET_PACKAGES[@]}"
}

print_post_install_tips() {
	cat <<EOF

------------------------------------------------------------------------
XFCE session installed.

• i3 remains your default window manager. We did not modify ~/.xinitrc,
  display manager defaults, or systemd targets.
• At your next graphical login, pick "${TARGET_SESSION_NAME}" (or "Xfce"),
  then log in to enjoy compositing via xfwm4.
• Once you are done testing Unity, simply log out and choose i3 again.

We'll log you out now so you can switch sessions safely.
------------------------------------------------------------------------
EOF
}

logout_user() {
	local session_id="${XDG_SESSION_ID:-}"

	if [[ -n $session_id ]] && loginctl show-session "$session_id" >/dev/null 2>&1; then
		info "Terminating current session (ID: $session_id) via loginctl."
		loginctl terminate-session "$session_id"
		return
	fi

	if loginctl list-sessions 2>/dev/null | awk '{print $1" "$3}' | grep -q " $USER$"; then
		info "Terminating all sessions for user '$USER' via loginctl."
		loginctl terminate-user "$USER"
		return
	fi

	warn "loginctl could not terminate the session; attempting fallback logout."
	pkill -KILL -u "$USER" || error "Failed to terminate user sessions. Please log out manually."
}

main() {
	ensure_pacman
	install_packages
	print_post_install_tips

	# Give the user a moment to read the instructions before logging out.
	logout_user
}

main "$@"

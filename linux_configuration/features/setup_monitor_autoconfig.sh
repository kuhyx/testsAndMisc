#!/bin/bash
# setup_monitor_autoconfig.sh — every monitor at its best mode, automatically.
#
# Installs the monitor-autoconfig systemd user service. It applies the layout
# at login and again whenever a monitor is plugged or unplugged:
#   - each monitor runs its native resolution at the highest refresh rate;
#   - DP-0 is primary and leftmost, the others sit to its right;
#   - an unplugged monitor is switched off so no gap is left.
# Policy lives in monitor_layout.py; the watcher in monitor_autoconfig.py.
#
# Run as your normal user (never with sudo). Idempotent: rerun after edits.
# Uninstall: systemctl --user disable --now monitor-autoconfig.service

set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
readonly HERE
readonly UNIT=monitor-autoconfig.service
readonly UNIT_DIR="$HOME/.config/systemd/user"

log() { printf '[monitor-autoconfig] %s\n' "$*"; }
die() {
	printf '[monitor-autoconfig] ERROR: %s\n' "$*" >&2
	exit 1
}

install_deps() {
	local pkg missing=()
	for pkg in python-xlib xorg-xrandr; do
		pacman -Q "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
	done
	if ((${#missing[@]})); then
		log "installing ${missing[*]}"
		sudo pacman -S --needed --noconfirm "${missing[@]}"
	fi
}

install_unit() {
	mkdir -p "$UNIT_DIR"
	sed "s|@FEATURES_DIR@|$HERE|" "$HERE/systemd/$UNIT" >"$UNIT_DIR/$UNIT"
	systemctl --user daemon-reload
	systemctl --user enable "$UNIT" >/dev/null
	systemctl --user restart "$UNIT"
}

main() {
	((EUID != 0)) || die "run as your normal user, not root"
	install_deps
	install_unit
	systemctl --user is-active --quiet "$UNIT" || die "$UNIT failed to start"
	log "active; layout now: $(xrandr --listmonitors | tail -n +2 | awk '{print $4}' | paste -sd' ')"
}

main "$@"

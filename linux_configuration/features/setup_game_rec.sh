#!/bin/bash

# ============================================================================
# Install game-rec (gaming/game_rec.sh): pacman deps, the ~/.local/bin/game-rec
# symlink, the i3blocks indicator symlink, the $mod+Shift+g hotkey in the
# live i3 config, and the game-rec-auto user service (gaming/game_rec_watch.sh,
# enabled at login, restarted here; recordings live in their own scopes, so a
# restart never stops one). Idempotent. It never reloads i3 or restarts
# i3blocks (a game may be running): it prints what to run instead.
# ============================================================================

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly REPO_DIR="${SCRIPT_DIR%/*}"
readonly PACKAGES=(gpu-screen-recorder xdotool xorg-xrandr util-linux coreutils procps-ng
	python-jeepney systemd)
# Single-quoted on purpose: i3 passes $HOME through to sh -c.
# shellcheck disable=SC2016
readonly HOTKEY='bindsym $mod+Shift+g exec --no-startup-id $HOME/.local/bin/game-rec toggle'
readonly I3_CONFIG="$HOME/.config/i3/config"
readonly UNIT=game-rec-auto.service
readonly UNIT_DIR="$HOME/.config/systemd/user"

install_packages() {
	local pkg
	local -a missing=()
	for pkg in "${PACKAGES[@]}"; do
		pacman -Q "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
	done
	((${#missing[@]} == 0)) || sudo pacman -S --needed --noconfirm "${missing[@]}"
}

link() {
	mkdir -p "${2%/*}"
	ln -sfn "$1" "$2"
}

add_hotkey() {
	if [[ ! -f $I3_CONFIG ]]; then
		printf 'skip hotkey: %s not found\n' "$I3_CONFIG"
		return 0
	fi
	grep -qF -- "$HOTKEY" "$I3_CONFIG" && return 0
	printf '\n# game recorder (linux_configuration/gaming/game_rec.sh)\n%s\n' \
		"$HOTKEY" >>"$I3_CONFIG"
}

install_unit() {
	mkdir -p "$UNIT_DIR"
	sed "s|@GAME_REC_DIR@|$REPO_DIR/gaming|" "$REPO_DIR/features/systemd/$UNIT" \
		>"$UNIT_DIR/$UNIT"
	systemctl --user daemon-reload
	systemctl --user enable "$UNIT" >/dev/null
	systemctl --user restart "$UNIT"
}

main() {
	install_packages
	chmod +x "$REPO_DIR/gaming/game_rec.sh" "$REPO_DIR/gaming/game_rec_watch.sh" \
		"$REPO_DIR/i3blocks/game_rec.sh"
	link "$REPO_DIR/gaming/game_rec.sh" "$HOME/.local/bin/game-rec"
	link "$REPO_DIR/i3blocks/game_rec.sh" "$HOME/.config/i3blocks/game_rec.sh"
	add_hotkey
	install_unit
	printf 'game-rec installed. To activate (not done here):\n'
	printf '  i3-msg restart (re-reads the hotkey, restarts i3bar + i3blocks)\n'
}

main "$@"

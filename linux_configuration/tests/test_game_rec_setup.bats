#!/usr/bin/env bats
# game_rec wiring: the i3 hotkey, the i3blocks block, and setup_game_rec.sh
# (run against a scratch HOME with stub pacman/sudo; it never reloads i3).
# The $mod / $HOME in single quotes are literal i3 config text, never expanded.
# shellcheck disable=SC2016

REPO_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SETUP="$REPO_DIR/features/setup_game_rec.sh"
readonly HOTKEY='bindsym $mod+Shift+g exec --no-startup-id $HOME/.local/bin/game-rec toggle'

setup() {
	export HOME="$BATS_TEST_TMPDIR/home"
	mkdir -p "$HOME/.config/i3" "$BATS_TEST_TMPDIR/bin"
	printf 'set $mod Mod4\nbindsym $mod+d exec dmenu_run\n' >"$HOME/.config/i3/config"
	cat >"$BATS_TEST_TMPDIR/bin/pacman" <<'EOF'
#!/bin/bash
[[ $1 == -Q && " ${MISSING_PKGS:-} " == *" $2 "* ]] && exit 1
exit 0
EOF
	cat >"$BATS_TEST_TMPDIR/bin/sudo" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >>"$HOME/sudo_calls"
EOF
	cat >"$BATS_TEST_TMPDIR/bin/i3-msg" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >>"$HOME/i3msg_calls"
EOF
	# Never the real user manager: kuhy's watcher may be live.
	cat >"$BATS_TEST_TMPDIR/bin/systemctl" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >>"$HOME/systemctl_calls"
EOF
	chmod +x "$BATS_TEST_TMPDIR/bin"/*
	export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
}

@test "repo i3 config binds \$mod+Shift+g to game-rec toggle, once" {
	[ "$(grep -cF "$HOTKEY" "$REPO_DIR/i3/config")" -eq 1 ]
	[ "$(grep -cE '^\s*bindsym \$mod\+Shift\+g ' "$REPO_DIR/i3/config")" -eq 1 ]
}

@test "i3blocks config: game_rec block is signal-driven, no polling" {
	block=$(sed -n '/^\[game_rec\]$/,/^$/p' "$REPO_DIR/i3blocks/config")
	grep -qx 'command=~/.config/i3blocks/game_rec.sh' <<<"$block"
	grep -qx 'interval=once' <<<"$block"
	grep -qx 'signal=12' <<<"$block"
	[ "$(grep -cx 'signal=12' "$REPO_DIR/i3blocks/config")" -eq 1 ]
}

@test "setup links game-rec and the block, adds the hotkey once, no reload" {
	run bash "$SETUP"
	[ "$status" -eq 0 ]
	run bash "$SETUP"
	[ "$status" -eq 0 ]
	[ "$(readlink "$HOME/.local/bin/game-rec")" = "$REPO_DIR/gaming/game_rec.sh" ]
	[ "$(readlink "$HOME/.config/i3blocks/game_rec.sh")" = "$REPO_DIR/i3blocks/game_rec.sh" ]
	[ "$(grep -cF "$HOTKEY" "$HOME/.config/i3/config")" -eq 1 ]
	[ ! -e "$HOME/sudo_calls" ]
	[ ! -e "$HOME/i3msg_calls" ]
}

@test "setup installs only the missing packages" {
	MISSING_PKGS='xdotool' run bash "$SETUP"
	[ "$status" -eq 0 ]
	[ "$(cat "$HOME/sudo_calls")" = 'pacman -S --needed --noconfirm xdotool' ]
}

@test "setup installs and enables the auto watcher unit at login" {
	run bash "$SETUP"
	[ "$status" -eq 0 ]
	unit="$HOME/.config/systemd/user/game-rec-auto.service"
	grep -qx "ExecStart=/bin/bash $REPO_DIR/gaming/game_rec_watch.sh" "$unit"
	grep -qx 'WantedBy=graphical-session.target' "$unit"
	run ! grep -q '@GAME_REC_DIR@' "$unit"
	[ "$(cat "$HOME/systemctl_calls")" = $'--user daemon-reload\n--user enable game-rec-auto.service\n--user restart game-rec-auto.service' ]
}

@test "the setup package list includes jeepney for the D-Bus helper" {
	MISSING_PKGS='python-jeepney' run bash "$SETUP"
	[ "$status" -eq 0 ]
	[ "$(cat "$HOME/sudo_calls")" = 'pacman -S --needed --noconfirm python-jeepney' ]
}

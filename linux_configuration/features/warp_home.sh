#!/bin/bash
# ============================================================================
# warp_home.sh -- the work laptop's side of the home WARP window. No root.
#
# At home the PC drops the Cloudflare WARP tunnel (gateway mode), and WARP
# fails CLOSED: blocked, even stuck at "Connecting", it leaves the laptop with
# no internet at all, and Always On keeps reconnecting it. So a user timer
# runs `tick` every 30 s: at home, with no window open, it turns WARP off and
# plain internet (with the DNS blocklist) comes back. On any other network,
# e.g. the office, it never touches WARP.
#
#   warp-home on       Mon/Thu/Fri 07:00-17:00 at home: ask the PC, then connect.
#                      Anywhere else: just connect.
#   warp-home off      disconnect and forget the window
#   warp-home status   network, window, WARP and the PC's view
#   warp-home install  copy to ~/.local/bin, create the key, enable the timer
#
# The PC enforces the window (warp_window.sh); this only remembers the end
# it was told. Re-applying the PC firewall closes the window early: run
# `warp-home on` again.
# ============================================================================

set -euo pipefail

readonly PC_IP="192.168.1.43" PC_MAC="9c:6b:00:5c:c5:6d" PC_USER="kuhy"
readonly WARN_SEC=300 # warn five minutes before the 17:00 cut-off
KEY="$HOME/.ssh/warp_window_ed25519"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/warp-home"
OPEN_UNTIL="$STATE_DIR/open-until"
WARNED="$STATE_DIR/warned"

die() {
	printf 'warp-home: %s\n' "$1" >&2
	exit 1
}

warp() { warp-cli --accept-tos "$@"; }
notify() { notify-send -a warp-home "WARP" "$1" 2>/dev/null || true; }

# Home means the default gateway is the PC, by IP and by MAC, so another
# network that happens to use 192.168.1.43 does not count.
at_home() {
	local gw dev
	read -r _ _ gw _ dev _ <<<"$(ip -4 route show default | head -n1)"
	[[ $gw == "$PC_IP" ]] || return 1
	[[ $(ip neigh show "$gw" dev "$dev") == *"lladdr $PC_MAC"* ]]
}

window_open() {
	[[ -f $OPEN_UNTIL ]] && (($(date +%s) < $(<"$OPEN_UNTIL")))
}

forget_window() { rm -f "$OPEN_UNTIL" "$WARNED"; }

pc() {
	# accept-new: the first call learns the PC's host key (BatchMode would
	# refuse it outright), later calls refuse a changed one.
	ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5 \
		-o StrictHostKeyChecking=accept-new "$PC_USER@$PC_IP" "$1"
}

# Turn WARP off (it is blocked, so on it means offline) and say why.
warp_off_because() {
	forget_window
	[[ $(warp status) == *Disconnected* ]] && return 0
	warp disconnect >/dev/null
	notify "$1"
}

cmd_tick() {
	at_home || return 0
	window_open || {
		warp_off_because "WARP turned off at home. 'warp-home on' works Mon/Thu/Fri 07:00-17:00."
		return 0
	}
	# Any re-apply of the PC firewall empties its set before 17:00. Only an
	# explicit "closed" counts: an unreachable PC proves nothing.
	if [[ $(pc status 2>/dev/null) == closed ]]; then
		warp_off_because "The PC closed the WARP window early; run 'warp-home on' again."
		return 0
	fi
	if (($(<"$OPEN_UNTIL") - $(date +%s) <= WARN_SEC)) && [[ ! -e $WARNED ]]; then
		notify "WARP closes at 17:00, in five minutes."
		touch "$WARNED"
	fi
}

cmd_on() {
	local answer left
	if at_home; then
		answer="$(pc open)" || die "${answer:-the PC refused}"
		left="$(sed -n 's/^seconds_left=//p' <<<"$answer")"
		[[ $left =~ ^[0-9]+$ ]] || die "unexpected answer from the PC: $answer"
		mkdir -p "$STATE_DIR"
		rm -f "$WARNED"
		printf '%s\n' "$(($(date +%s) + left))" >"$OPEN_UNTIL"
	fi
	warp connect >/dev/null
	printf 'WARP connecting.%s\n' "$(at_home && printf ' Home window ends at 17:00.')"
}

cmd_off() {
	forget_window
	warp disconnect >/dev/null
	printf 'WARP off.\n'
}

cmd_status() {
	if at_home; then
		printf 'network: home\nwindow:  %s\npc:      %s\n' \
			"$(window_open && printf open || printf closed)" "$(pc status 2>&1 || true)"
	else
		printf 'network: not home (WARP is not managed here)\n'
	fi
	printf 'warp:    %s\n' "$(warp status | head -n1)"
}

cmd_install() {
	local bin="$HOME/.local/bin/warp-home" units="$HOME/.config/systemd/user"
	mkdir -p "${bin%/*}" "$units" "$HOME/.ssh"
	install -m 0755 "${BASH_SOURCE[0]}" "$bin"
	[[ -f $KEY ]] || ssh-keygen -q -t ed25519 -N '' -C warp-home -f "$KEY"
	cat >"$units/warp-home.service" <<EOF
[Unit]
Description=Turn WARP off at home outside the work-from-home window

[Service]
Type=oneshot
ExecStart=$bin tick
EOF
	cat >"$units/warp-home.timer" <<EOF
[Unit]
Description=Check WARP against the home window every 30 s

[Timer]
OnBootSec=30s
OnUnitActiveSec=30s
AccuracySec=5s

[Install]
WantedBy=timers.target
EOF
	systemctl --user daemon-reload
	systemctl --user enable --now warp-home.timer
	printf 'Installed. On the PC: sudo warp_window.sh install %s.pub\n' "$KEY"
}

main() {
	case "${1:-}" in
	on | off | status | tick | install) "cmd_$1" ;;
	*)
		printf 'usage: warp-home on|off|status|install\n' >&2
		exit 2
		;;
	esac
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
	main "$@"
fi

#!/usr/bin/env bash
# Tests for warp_home.sh -- the laptop side of the work-from-home WARP window.
#
# WARP fails closed: blocked at the home gateway it leaves the laptop with no
# internet at all, and Always On keeps reconnecting it. The tick therefore
# turns WARP off whenever the laptop is home and no window is open, and must
# never touch it anywhere else (the office network always gets WARP).
# ip, warp-cli, ssh, notify-send and the clock are stubbed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

HOME="$TEST_TMPDIR/home"
XDG_STATE_HOME="$HOME/.local/state"
mkdir -p "$HOME"
# shellcheck source=../../warp_home.sh
. "$FEATURES_LIB_DIR/../warp_home.sh"

FAKE_EPOCH=1000000
date() { printf '%s\n' "$FAKE_EPOCH"; }
ROUTE="default via 192.168.1.43 dev wlp4s0 proto dhcp src 192.168.1.21"
NEIGH="192.168.1.43 dev wlp4s0 lladdr 9c:6b:00:5c:c5:6d REACHABLE"
ip() {
	case "$*" in
	*route*) printf '%s\n' "$ROUTE" ;;
	*neigh*) printf '%s\n' "$NEIGH" ;;
	esac
}
WARP_STATE="Status update: Connected"
warp-cli() {
	printf 'warp-cli %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
	[[ $* == *status* ]] && printf '%s\n' "$WARP_STATE"
	return 0
}
SSH_OUT="seconds_left=600"
SSH_RC=0
ssh() {
	printf 'ssh %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
	printf '%s\n' "$SSH_OUT"
	return "$SSH_RC"
}
_t_stub notify-send
reset_calls() { : >"$TEST_TMPDIR/calls.log"; }
not_called() {
	if grep -q "$1" "$TEST_TMPDIR/calls.log" 2>/dev/null; then _t_fail "$2"; else _t_pass "$2"; fi
}

printf '\n-- home is the PC as gateway, by IP AND MAC --\n'
_t_ok "the PC as default gateway is home" at_home
ROUTE="default via 10.20.0.1 dev wlp4s0"
_t_not "an office gateway is not home" at_home
ROUTE="default via 192.168.1.43 dev wlp4s0 proto dhcp"
NEIGH="192.168.1.43 dev wlp4s0 lladdr 02:11:22:33:44:55 REACHABLE"
_t_not "the same IP with another MAC is not home" at_home
NEIGH="192.168.1.43 dev wlp4s0 lladdr 9c:6b:00:5c:c5:6d REACHABLE"

printf '\n-- tick: away from home WARP is never touched --\n'
ROUTE="default via 10.20.0.1 dev wlp4s0"
reset_calls
cmd_tick
not_called 'warp-cli' "the tick ignores WARP on the office network"
ROUTE="default via 192.168.1.43 dev wlp4s0 proto dhcp"

printf '\n-- tick at home: WARP goes off unless a window is open --\n'
reset_calls
cmd_tick
_t_called 'warp-cli --accept-tos disconnect' "a connected WARP is disconnected at home"
_t_called 'notify-send' "the disconnect is announced"
WARP_STATE="Status update: Disconnected"
reset_calls
cmd_tick
not_called 'disconnect' "an already disconnected WARP is left alone"
WARP_STATE="Status update: Connecting"
reset_calls
cmd_tick
_t_called 'disconnect' "a WARP stuck connecting (fail-closed) is disconnected"

printf '\n-- on: the PC decides, the laptop only remembers --\n'
WARP_STATE="Status update: Disconnected"
reset_calls
cmd_on >/dev/null
_t_called "ssh .*kuhy@192.168.1.43 open" "on asks the PC to open the window"
_t_called 'warp-cli --accept-tos connect' "on connects WARP after the PC agreed"
_t_eq "1000600" "$(cat "$OPEN_UNTIL")" "the window end is stored from the PC's answer"
reset_calls
WARP_STATE="Status update: Connected"
FAKE_EPOCH=1000300
cmd_tick
not_called 'disconnect' "an open window keeps WARP on"
_t_called 'notify-send' "five minutes before the cut-off kuhy is warned"
reset_calls
cmd_tick
not_called 'notify-send' "the warning is sent once"
FAKE_EPOCH=1000600
reset_calls
cmd_tick
_t_called 'disconnect' "at the window end WARP is disconnected"
_t_not "the expired window is forgotten" test -e "$OPEN_UNTIL"

printf '\n-- tick: a window the PC already closed does not strand the laptop --\n'
FAKE_EPOCH=1000000
printf '1000600\n' >"$OPEN_UNTIL"
SSH_RC=255
SSH_OUT=""
reset_calls
cmd_tick
not_called 'disconnect' "an unreachable PC leaves WARP alone"
SSH_RC=0
SSH_OUT="closed"
reset_calls
cmd_tick
_t_called 'ssh .* status' "an open window is checked against the PC"
_t_called 'disconnect' "a window the PC closed early disconnects WARP"
_t_not "the early-closed window is forgotten" test -e "$OPEN_UNTIL"
SSH_OUT="seconds_left=600"

printf '\n-- on: a refusal connects nothing --\n'
SSH_OUT="WARP window is Mon/Fri 09:00-15:30 only"
SSH_RC=1
reset_calls
on_refused() { cmd_on; }
_t_exits_nonzero on_refused "a refused on exits non-zero"
not_called 'connect' "a refused on does not connect WARP"
SSH_RC=0
SSH_OUT="seconds_left=600"

printf '\n-- on away from home just connects --\n'
ROUTE="default via 10.20.0.1 dev wlp4s0"
reset_calls
cmd_on >/dev/null
not_called '^ssh' "on at the office asks nobody"
_t_called 'warp-cli --accept-tos connect' "on at the office connects WARP"
ROUTE="default via 192.168.1.43 dev wlp4s0 proto dhcp"

printf '\n-- off forgets the window and disconnects --\n'
printf '2000000\n' >"$OPEN_UNTIL"
reset_calls
cmd_off >/dev/null
_t_called 'disconnect' "off disconnects WARP"
_t_not "off forgets the window" test -e "$OPEN_UNTIL"

printf '\n-- install: a user timer every 30 s, a dedicated key --\n'
_t_stub systemctl
_t_stub ssh-keygen
cmd_install >/dev/null
_t_file_has "$HOME/.config/systemd/user/warp-home.timer" '^OnUnitActiveSec=30s$' "the tick runs every 30 s"
_t_file_has "$HOME/.config/systemd/user/warp-home.service" "^ExecStart=$HOME/.local/bin/warp-home tick$" \
	"the service runs the installed copy"
_t_called 'systemctl --user enable --now warp-home.timer' "the timer is enabled for the user, no root"
_t_called "ssh-keygen .*$HOME/.ssh/warp_window_ed25519" "a dedicated key is generated"
_t_ok "the script is installed executable" test -x "$HOME/.local/bin/warp-home"

printf '\n-- status and usage --\n'
SSH_OUT="closed"
out="$(cmd_status)"
_t_has "$out" "network: home" "status names the home network"
_t_has "$out" "pc:      closed" "status shows the PC's view"
ROUTE="default via 10.20.0.1 dev wlp4s0"
_t_has "$(cmd_status)" "not home" "status away from home says WARP is not managed"
usage() { main bogus; }
_t_exits_nonzero usage "an unknown command exits non-zero"

_t_report "test_warp_home.sh"

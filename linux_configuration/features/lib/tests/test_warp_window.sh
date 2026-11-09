#!/usr/bin/env bash
# Tests for warp_window.sh -- the PC side of the work-from-home WARP window.
#
# Gateway mode drops the Cloudflare WARP tunnel because it carries everything
# past the DNS block. kuhy may open it only Mon/Thu/Fri 07:00-17:00; the laptop
# asks over an SSH key whose forced command can run nothing but open/status.
# The window edges and the forced-command filter are the security boundary,
# so both are asserted exactly. The clock and nft are stubbed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# shellcheck source=../../warp_window.sh
. "$FEATURES_LIB_DIR/../warp_window.sh"

# `date +%u %H %M %S` as warp_window.sh asks for it.
FAKE_DATE="1 10 00 00"
date() { printf '%s\n' "$FAKE_DATE"; }
_t_stub nft

left_at() {
	FAKE_DATE="$1"
	window_seconds_left || printf 'closed'
}

printf '\n-- the window is Mon/Thu/Fri 07:00-17:00, nothing else --\n'
_t_eq "closed" "$(left_at '1 06 59 59')" "Monday 06:59:59 is closed"
_t_eq "36000" "$(left_at '1 07 00 00')" "Monday 07:00 opens until 17:00"
_t_eq "1" "$(left_at '1 16 59 59')" "Monday 16:59:59 has one second left"
_t_eq "closed" "$(left_at '1 17 00 00')" "Monday 17:00 is closed"
_t_eq "18000" "$(left_at '5 12 00 00')" "Friday noon is open"
_t_eq "36000" "$(left_at '4 07 00 00')" "Thursday 07:00 opens until 17:00"
_t_eq "closed" "$(left_at '4 17 00 00')" "Thursday 17:00 is closed"
for day in 2 3 6 7; do
	_t_eq "closed" "$(left_at "$day 12 00 00")" "weekday $day noon is closed"
done
_t_eq "31860" "$(left_at '5 08 09 00')" "a leading-zero hour is decimal, not octal"

printf '\n-- open fills the set with a timeout ending at 17:00 --\n'
FAKE_DATE="1 10 00 00"
out="$(cmd_open)"
_t_called 'nft add element inet filter warp_open { 0.0.0.0/0 timeout 25200s }' \
	"open adds the catch-all element with the time left"
_t_has "$out" "seconds_left=25200" "open reports the seconds left for the laptop"
_t_has "$out" "until 17:00" "open names the 17:00 cut-off"

printf '\n-- outside the window open refuses and touches nothing --\n'
: >"$TEST_TMPDIR/calls.log"
FAKE_DATE="3 12 00 00"
open_wed() { cmd_open; }
_t_exits_nonzero open_wed "open on a Wednesday exits non-zero"
if grep -q 'add element' "$TEST_TMPDIR/calls.log"; then
	_t_fail "a refused open adds no element"
else
	_t_pass "a refused open adds no element"
fi

printf '\n-- the forced command allows only open and status --\n'
FAKE_DATE="5 10 00 00"
: >"$TEST_TMPDIR/calls.log"
ssh_as() { SSH_ORIGINAL_COMMAND="$1" cmd_ssh; }
ssh_close() { ssh_as close; }
ssh_inject() { ssh_as 'open; rm -rf /'; }
ssh_empty() { ssh_as ''; }
_t_exits_nonzero ssh_close "close is refused over ssh"
_t_exits_nonzero ssh_inject "a chained command is refused over ssh"
_t_exits_nonzero ssh_empty "an interactive login is refused"
ssh_as open >/dev/null
_t_called 'add element inet filter warp_open' "open is allowed over ssh"

printf '\n-- close empties the set --\n'
cmd_close >/dev/null
_t_called 'nft flush set inet filter warp_open' "close flushes the set"

printf '\n-- install: sudoers checked by visudo, one forced-command key line --\n'
_t_stub visudo
_t_stub chown
INSTALL_PATH="$TEST_TMPDIR/warp-window"
SUDOERS_FILE="$TEST_TMPDIR/sudoers-warp-window"
KEY_HOME="$TEST_TMPDIR/home"
KEY_USER="kuhy"
mkdir -p "$KEY_HOME/.ssh"
printf 'ssh-ed25519 AAAAexisting other\n' >"$KEY_HOME/.ssh/authorized_keys"
printf 'ssh-ed25519 AAAAlaptop warp-home\n' >"$TEST_TMPDIR/laptop.pub"
cmd_install "$TEST_TMPDIR/laptop.pub" >/dev/null
cmd_install "$TEST_TMPDIR/laptop.pub" >/dev/null
_t_called 'visudo -cf' "the sudoers drop-in is syntax-checked"
_t_file_has "$SUDOERS_FILE" "^kuhy ALL=(root) NOPASSWD: $INSTALL_PATH ssh$" \
	"sudoers allows only the ssh entry point"
_t_file_has "$SUDOERS_FILE" "^Defaults!$INSTALL_PATH env_keep += \"SSH_ORIGINAL_COMMAND\"$" \
	"sudo keeps the client's command for the filter"
_t_file_has "$KEY_HOME/.ssh/authorized_keys" \
	"^restrict,from=\"192.168.1.0/24\",command=\"sudo -n $INSTALL_PATH ssh\" ssh-ed25519 AAAAlaptop warp-home\$" \
	"the laptop key is restricted to the forced command from the LAN"
_t_eq "1" "$(grep -c AAAAlaptop "$KEY_HOME/.ssh/authorized_keys")" "reinstalling keeps one key line"
_t_file_has "$KEY_HOME/.ssh/authorized_keys" "AAAAexisting other" "other keys are kept"
_t_ok "the script is installed executable" test -x "$INSTALL_PATH"

printf '\n-- status, usage and install failures --\n'
NFT_LIST="elements = { 0.0.0.0/0 timeout 5h expires 4h59m58s }"
nft() { printf '%s\n' "$NFT_LIST"; }
_t_eq "open (expires 4h59m58s)" "$(cmd_status)" "status shows when an open window expires"
NFT_LIST="flags interval,timeout"
_t_eq "closed" "$(cmd_status)" "status shows an empty set as closed"
unset -f nft
usage() { main bogus; }
_t_exits_nonzero usage "an unknown command exits non-zero"
no_pub() { cmd_install "$TEST_TMPDIR/missing.pub"; }
_t_exits_nonzero no_pub "install without a key file refuses"
rm -f "$SUDOERS_FILE"
printf '#!/usr/bin/env bash\nexit 1\n' >"$TEST_TMPDIR/bin/visudo"
bad_sudoers() { cmd_install "$TEST_TMPDIR/laptop.pub"; }
_t_exits_nonzero bad_sudoers "install refuses a drop-in visudo rejects"
_t_not "a rejected drop-in is never installed" test -e "$SUDOERS_FILE"

_t_report "test_warp_window.sh"

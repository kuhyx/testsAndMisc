#!/usr/bin/env bash
# Tests for wg_verify_units.sh — the units that run 'verify' by themselves.
#
# The generated CONTENT is the whole subject. A unit that exists but is
# ordered before nftables.service compares /etc/nftables.conf against the
# previous boot's ruleset; a unit that logs instead of exiting non-zero is a
# warning nobody reads. Both look identical to a presence check, and both
# reproduce the outage this exists to catch.
#
# Rendering writes only where it is told, so unlike its siblings this suite
# needs no jail to be safe -- but it runs inside one with the rest of the
# directory, and must not assume it can reach the real /etc.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# shellcheck source=../wg_verify_units.sh
. "$SCRIPT_DIR/../wg_verify_units.sh"

readonly ENTRY="/home/kuhy/testsAndMisc/linux_configuration/features/setup_wireguard_ssh.sh"
UNIT_DIR="$TEST_TMPDIR/units"
mkdir -p "$UNIT_DIR"

render_verify_units "$UNIT_DIR" "$ENTRY"

SERVICE="${UNIT_DIR}/${VERIFY_SERVICE}"
TIMER="${UNIT_DIR}/${VERIFY_TIMER}"

printf '\n-- the service runs the repo checkout, not a copy --\n'
_t_file_has "$SERVICE" "^ExecStart=${ENTRY} verify\$" \
	"ExecStart invokes the entry script's verify subcommand"
_t_file_has "$SERVICE" '^Type=oneshot$' "one shot, not a daemon"

printf '\n-- ordering: check the ruleset that is actually loaded --\n'
# Before nftables.service, the check reads whatever the previous boot left.
_t_file_has "$SERVICE" '^After=.*nftables\.service' "ordered after nftables.service"
_t_file_has "$SERVICE" '^After=.*docker\.service' "ordered after docker.service"
# detect_lan_subnet shells out to `ip route get` when LAN_SUBNET is unset, and
# dies if there is no route yet -- indistinguishable from real drift.
_t_file_has "$SERVICE" '^After=.*network-online\.target' "ordered after the network is up"
if grep -q '^Requires=' "$SERVICE"; then
	_t_fail "Requires= would skip the check when nftables.service is dead, which is the worst fault it detects"
else
	_t_pass "no Requires=, so a dead nftables.service still fails this unit"
fi

printf '\n-- it may not write anything --\n'
_t_file_has "$SERVICE" '^ProtectHome=read-only$' \
	"cannot root-rewrite the saved LAN_SUBNET in the repo"
_t_file_has "$SERVICE" '^ProtectSystem=strict$' "cannot rewrite /etc"

printf '\n-- it runs at boot, and again on a timer --\n'
_t_file_has "$SERVICE" '^WantedBy=multi-user\.target$' "enabled at boot"
_t_file_has "$TIMER" "^Unit=${VERIFY_SERVICE}\$" "the timer triggers that same service"
_t_file_has "$TIMER" '^Persistent=true$' "a PC that was off still checks when it returns"
_t_file_has "$TIMER" '^WantedBy=timers\.target$' "the timer is enabled at boot too"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]

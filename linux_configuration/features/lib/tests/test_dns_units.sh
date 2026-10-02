#!/usr/bin/env bash
# Tests for dns_units.sh -- the dnsmasq config and its systemd drop-in.
#
# Both regressions this guards were invisible to a presence check. With
# bind-interfaces, dnsmasq died at every boot ("unknown interface enp6s0")
# because it started before the NIC existed. The drop-in's
# After=network-online.target formed an ordering cycle with the stock unit's
# Before=network-online.target, and systemd broke it by deleting a job.
#
# Rendering writes only where it is told, so this suite needs no jail.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

ensure_dir() { mkdir -p "$1"; }
log_info() { :; }

# shellcheck source=../dns_units.sh
. "$SCRIPT_DIR/../dns_units.sh"

DNSMASQ_CONF="$TEST_TMPDIR/dnsmasq.d/lan-blocker.conf"
DNSMASQ_DROPIN_DIR="$TEST_TMPDIR/dnsmasq.service.d"
DNSMASQ_DROPIN="$DNSMASQ_DROPIN_DIR/blocker.conf"
LAN_IFACE="enp6s0"
LAN_IP="192.168.1.43"
UPSTREAM="1.1.1.1"
FEED="$TEST_TMPDIR/blocklist.hosts"
LOG_FILE="$TEST_TMPDIR/dnsmasq.log"

write_dnsmasq_conf
install_restart_dropin

printf '\n-- dnsmasq survives starting before the NIC exists --\n'
_t_file_has "$DNSMASQ_CONF" '^interface=enp6s0$' "listens only on the LAN interface"
_t_file_has "$DNSMASQ_CONF" '^bind-dynamic$' "binds the address whenever the interface appears"
if grep -q '^bind-interfaces' "$DNSMASQ_CONF"; then
	_t_fail "bind-interfaces exits with 'unknown interface' when started before the NIC"
else
	_t_pass "no bind-interfaces"
fi

printf '\n-- the drop-in keeps it up without an ordering cycle --\n'
_t_file_has "$DNSMASQ_DROPIN" '^Restart=always$' "restarts on any exit"
if grep -qE '^(After|Wants|Requires)=.*network-online' "$DNSMASQ_DROPIN"; then
	_t_fail "network-online ordering cycles with the stock Before=network-online.target"
else
	_t_pass "no network-online ordering"
fi

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]

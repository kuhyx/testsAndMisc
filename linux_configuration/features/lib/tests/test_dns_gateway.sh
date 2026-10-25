#!/usr/bin/env bash
# Tests for dns_gateway.sh -- gateway mode for the LAN DNS blocker.
#
# Voluntary DNS let an Ubuntu laptop reach a blocked site on 2026-10-24: it
# took a lease naming this PC as DNS and resolved elsewhere anyway. Gateway
# mode routes other devices through the PC so DNS can be forced. The one
# thing it may never do is take the PC itself offline, so the self-check and
# its rollback are asserted on the commands actually called.
#
# Every write target is a scratch path and every command is stubbed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

log_info() { :; }
log_ok() { log "$1"; }
log_warn() { log "$1"; }
log_error() { log "$1"; }
die() {
	log "$1"
	exit 1
}

# shellcheck source=../dns_gateway.sh
. "$FEATURES_LIB_DIR/dns_gateway.sh"

LAN_IFACE="enp6s0"
LAN_IP="192.168.1.43"
GATEWAY="192.168.1.1"
GATEWAY_CONF="$TEST_TMPDIR/lan-gateway.conf"
GATEWAY_SYSCTL="$TEST_TMPDIR/90-lan-gateway.conf"
GATEWAY_DOCKER_UNIT="$TEST_TMPDIR/lan-gateway-docker-forward.service"

printf '\n-- DHCP hands out the PC as gateway, exempt devices keep the Funbox --\n'
render_gateway_dnsmasq_conf "$GATEWAY_CONF"
_t_file_has "$GATEWAY_CONF" '^dhcp-option=tag:!direct,option:router,192.168.1.43$' \
	"every other device gets the PC as router"
_t_file_has "$GATEWAY_CONF" '^dhcp-option=tag:direct,option:router,192.168.1.1$' \
	"exempt devices keep the Funbox as router"
_t_file_has "$GATEWAY_CONF" '^dhcp-host=2c:cf:67:1e:35:3a,set:direct$' "nextcloud-pi is exempt"
_t_file_has "$GATEWAY_CONF" '^dhcp-host=58:04:4f:db:c9:e8,set:direct$' "the P110 plug is exempt"

printf '\n-- the kernel forwards and never redirects clients past the PC --\n'
render_gateway_sysctl "$GATEWAY_SYSCTL"
_t_file_has "$GATEWAY_SYSCTL" '^net.ipv4.ip_forward = 1$' "forwarding on"
_t_file_has "$GATEWAY_SYSCTL" '^net.ipv4.conf.all.send_redirects = 0$' "no redirects (all)"
_t_file_has "$GATEWAY_SYSCTL" '^net.ipv4.conf.enp6s0.send_redirects = 0$' "no redirects (LAN NIC)"

printf '\n-- Docker'"'"'s legacy FORWARD DROP lets LAN traffic through --\n'
render_docker_user_unit "$GATEWAY_DOCKER_UNIT"
_t_file_has "$GATEWAY_DOCKER_UNIT" 'iptables -I DOCKER-USER -i enp6s0 -o enp6s0 -j ACCEPT' \
	"inserts the accept into DOCKER-USER"
_t_file_has "$GATEWAY_DOCKER_UNIT" '^PartOf=docker.service$' "re-applied whenever docker restarts"
_t_file_has "$GATEWAY_DOCKER_UNIT" '^WantedBy=docker.service$' "started with docker"

printf '\n-- the PC staying online is checked, and a failure rolls back --\n'
_t_stub systemctl
cmd_gateway_off() { printf 'ROLLBACK\n' >>"$TEST_TMPDIR/calls.log"; }
pc_route() { printf '1.1.1.1 via 192.168.1.1 dev enp6s0 src 192.168.1.43\n'; }
pc_ping() { return 0; }
pc_resolve() { return 0; }
blocker_answers() { return 0; }
if gateway_self_check; then
	_t_pass "a healthy PC passes the self-check"
else
	_t_fail "a healthy PC passes the self-check"
fi
pc_route() { printf '1.1.1.1 via 192.168.1.43 dev enp6s0\n'; }
if gateway_self_check; then
	_t_fail "a default route away from the Funbox fails the self-check"
else
	_t_pass "a default route away from the Funbox fails the self-check"
fi
pc_route() { printf '1.1.1.1 via 192.168.1.1 dev enp6s0 src 192.168.1.43\n'; }
pc_ping() { return 1; }
if gateway_self_check; then
	_t_fail "no internet on the PC fails the self-check"
else
	_t_pass "no internet on the PC fails the self-check"
fi
_t_exits_nonzero apply_or_rollback "a failed self-check aborts the apply"
_t_file_has "$TEST_TMPDIR/calls.log" '^ROLLBACK$' "a failed self-check rolls gateway mode back"

_t_report "test_dns_gateway.sh"

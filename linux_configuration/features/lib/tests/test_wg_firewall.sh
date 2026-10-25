#!/usr/bin/env bash
# Tests for wg_firewall.sh -- the rendered ruleset and the docker restart.
#
# Every apply used to start with 'flush ruleset' and end with a docker
# restart, so opening one port bounced every container on the host. The
# subject now replaces only its own table and restarts docker only when
# docker's own rules are really gone; both are asserted on generated content
# and on the commands actually called.
#
# Rendering writes only where it is told and every command is stubbed, so
# this suite needs no jail, but it runs inside one with its siblings.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

_t_setup_env
trap _t_teardown EXIT

# The globals setup_wireguard_ssh.sh defines above its source line.
WG_IFACE="wg0"
WG_PORT="51820"
LAN_SUBNET="192.168.1.0/24"
NFT_CONF="$TEST_TMPDIR/nftables.conf"
ALLOW_WEB="true"
ALLOW_DNS="false"
ALLOW_HOMEASSISTANT="true"
ALLOW_DOT="true"
detect_lan_subnet() { :; }
log_ok() { log "$1"; }
log_warn() { log "$1"; }
log_error() { log "$1"; }
die() {
	log "$1"
	exit 1
}
is_service_active() { [[ ${DOCKER_ACTIVE:-yes} == yes ]]; }

# shellcheck source=../wg_gateway.sh
. "$FEATURES_LIB_DIR/wg_gateway.sh"
# shellcheck source=../wg_firewall.sh
. "$FEATURES_LIB_DIR/wg_firewall.sh"

printf '\n-- only our own table is replaced --\n'
RULES="$TEST_TMPDIR/rules.nft"
render_nftables_ruleset "$RULES"
if grep -q '^flush ruleset' "$RULES"; then
	_t_fail "no 'flush ruleset' (it deletes Docker's and Tailscale's tables)"
else
	_t_pass "no 'flush ruleset' (it deletes Docker's and Tailscale's tables)"
fi
_t_eq "table inet filter|delete table inet filter" \
	"$(grep -E '^(delete )?table inet filter$' "$RULES" | paste -sd'|')" \
	"declare-then-delete precedes the definition, so a first boot loads"

printf '\n-- flags render their rules --\n'
_t_file_has "$RULES" 'iifname "wg0" tcp dport 853 accept' "ALLOW_DOT opens 853 on wg0"
_t_file_has "$RULES" 'iifname "wg0" tcp dport 8123 accept' "ALLOW_HOMEASSISTANT keeps 8123"
_t_file_has "$RULES" 'tcp dport { 80, 443 } accept' "ALLOW_WEB keeps 80/443"
ALLOW_DOT="false"
render_nftables_ruleset "$RULES"
if grep -q 'dport 853' "$RULES"; then
	_t_fail "ALLOW_DOT=false renders no 853 rule"
else
	_t_pass "ALLOW_DOT=false renders no 853 rule"
fi
printf '\n-- the workout poke is LAN-only --\n'
if grep -q 'dport 8774' "$RULES"; then
	_t_fail "ALLOW_WORKOUT_POKE unset renders no 8774 rule"
else
	_t_pass "ALLOW_WORKOUT_POKE unset renders no 8774 rule"
fi
ALLOW_WORKOUT_POKE="true"
render_nftables_ruleset "$RULES"
_t_file_has "$RULES" 'ip saddr 192.168.1.0/24 tcp dport 8774 accept' \
	"ALLOW_WORKOUT_POKE opens 8774 to the LAN subnet"
_t_eq "1" "$(grep -c 'dport 8774' "$RULES")" \
	"exactly one 8774 rule: no wg0 rule, the poke never rides WireGuard"
ALLOW_WORKOUT_POKE="false"
render_nftables_ruleset "$RULES"
if grep -q 'dport 8774' "$RULES"; then
	_t_fail "ALLOW_WORKOUT_POKE=false renders no 8774 rule"
else
	_t_pass "ALLOW_WORKOUT_POKE=false renders no 8774 rule"
fi
if command -v nft >/dev/null 2>&1; then
	ALLOW_DOT="true"
	ALLOW_WORKOUT_POKE="true"
	render_nftables_ruleset "$RULES"
	if nft -c -f "$RULES" >/dev/null 2>&1; then
		_t_pass "nft -c accepts the rendered ruleset"
	else
		# nft -c needs CAP_NET_ADMIN; outside the jail it cannot check at all.
		printf '  (skipped: nft -c not permitted here)\n'
	fi
fi

printf '\n-- docker is restarted only when its rules are gone --\n'
_t_stub systemctl
printf '#!/usr/bin/env bash\nprintf "iptables %%s\\n" "$*" >>"%s/calls.log"\nexit 0\n' \
	"$TEST_TMPDIR" >"$TEST_TMPDIR/bin/iptables"
chmod +x "$TEST_TMPDIR/bin/iptables"
out="$(restore_docker_rules 2>&1)"
_t_has "$out" 'intact; containers untouched' "intact docker rules are left alone"
if grep -q 'systemctl restart docker' "$TEST_TMPDIR/calls.log"; then
	_t_fail "no docker restart while its rules are intact"
else
	_t_pass "no docker restart while its rules are intact"
fi

printf '#!/usr/bin/env bash\nexit 1\n' >"$TEST_TMPDIR/bin/iptables"
out="$(restore_docker_rules 2>&1)"
_t_has "$out" 'restarted' "missing docker rules trigger a rebuild"
_t_called 'systemctl restart docker' "the rebuild is a docker restart"

: >"$TEST_TMPDIR/calls.log"
DOCKER_ACTIVE=no restore_docker_rules
if grep -q 'iptables\|systemctl' "$TEST_TMPDIR/calls.log"; then
	_t_fail "an inactive docker is not touched"
else
	_t_pass "an inactive docker is not touched"
fi

printf '\n-- allow-workout-poke persists the flag, then applies it --\n'
# save_config belongs to setup_wireguard_ssh.sh and the apply needs root, so
# both are recorded instead; the ruleset itself is the real render.
save_config() {
	printf 'save_config ALLOW_WORKOUT_POKE=%s\n' "$ALLOW_WORKOUT_POKE" >>"$TEST_TMPDIR/calls.log"
}
verify_nftables_then_apply() { printf 'apply\n' >>"$TEST_TMPDIR/calls.log"; }
: >"$TEST_TMPDIR/calls.log"
rm -f "$NFT_CONF" "${NFT_CONF}.new"
ALLOW_WORKOUT_POKE="false"
out="$(allow_workout_poke 2>&1)"
mapfile -t calls <"$TEST_TMPDIR/calls.log"
_t_eq "save_config ALLOW_WORKOUT_POKE=true|apply" "$(IFS='|' && printf '%s' "${calls[*]}")" \
	"the flag is saved as true before the ruleset is applied"
_t_file_has "${NFT_CONF}.new" 'ip saddr 192.168.1.0/24 tcp dport 8774 accept' \
	"the applied ruleset carries the LAN-only 8774 rule"
_t_has "$out" 'not wg0' "the confirmation says the port stays off WireGuard"

printf '\n-- LAN gateway mode --\n'
LAN_IFACE="enp6s0"
LAN_IP="192.168.1.43"
ALLOW_LAN_GATEWAY="false"
render_nftables_ruleset "$RULES"
_t_eq "table ip lan_gateway|delete table ip lan_gateway" \
	"$(grep -E '^(delete )?table ip lan_gateway$' "$RULES" | paste -sd'|')" \
	"gateway off still deletes a stale nat table on apply"
if grep -qE 'masquerade|dnat|oifname "enp6s0"' "$RULES"; then
	_t_fail "gateway off renders no forwarding or nat"
else
	_t_pass "gateway off renders no forwarding or nat"
fi
ALLOW_LAN_GATEWAY="true"
render_nftables_ruleset "$RULES"
_t_file_has "$RULES" 'iifname "enp6s0" oifname "enp6s0" ip saddr 192.168.1.0/24 accept' \
	"LAN traffic is forwarded back out of the same NIC"
_t_file_has "$RULES" 'iifname "enp6s0" ip saddr 192.168.1.0/24 ip daddr @doh_v4 drop' \
	"traffic to DoH resolvers is dropped"
_t_file_has "$RULES" 'iifname "enp6s0" ip saddr 192.168.1.0/24 tcp dport 853 drop' "DoT tcp/853 dropped"
_t_file_has "$RULES" 'iifname "enp6s0" ip saddr 192.168.1.0/24 udp dport 853 drop' "DoQ udp/853 dropped"
_t_file_has "$RULES" 'ip saddr != 192.168.1.43 ip daddr != 192.168.1.43 udp dport 53 dnat to 192.168.1.43' \
	"plain DNS to any server is redirected to the blocker"
_t_file_has "$RULES" 'oifname "enp6s0" ip saddr 192.168.1.0/24 ip saddr != 192.168.1.43 ip daddr != 192.168.1.0/24 masquerade' \
	"forwarded traffic is masqueraded, the PC's own is not"
doh_line=$(grep -n '@doh_v4 drop' "$RULES" | cut -d: -f1)
accept_line=$(grep -n 'oifname "enp6s0" ip saddr 192.168.1.0/24 accept' "$RULES" | cut -d: -f1)
if [[ -n $doh_line && -n $accept_line ]] && ((doh_line < accept_line)); then
	_t_pass "the DoH drop precedes the forward accept"
else
	_t_fail "the DoH drop precedes the forward accept"
fi
_t_file_has "$RULES" 'iifname "enp6s0" ip saddr 192.168.1.0/24 ip saddr != @warp_open ip daddr @warp_v4 drop' \
	"traffic to the WARP tunnel ingress is dropped unless the window is open"
_t_file_has "$RULES" 'iifname "enp6s0" ip saddr 192.168.1.0/24 ip saddr != @warp_open ip daddr @warp_udp_v4 meta l4proto udp drop' \
	"UDP to the shared consumer-WARP ranges is dropped unless the window is open"
_t_file_has "$RULES" 'set warp_open' "the WARP window set is declared"
_t_file_has "$RULES" 'flags interval,timeout' "the window set expires its elements by itself"
_t_file_has "$RULES" '162.159.193.0/24' "the WireGuard ingress is in the WARP set"
_t_file_has "$RULES" '162.159.197.0/24' "the MASQUE ingress (incl. its TCP 443 fallback) is in the WARP set"
_t_file_has "$RULES" '188.114.96.0/22' "consumer WARP endpoints are in the UDP-only set"
if grep -qE 'udp dport (500|1701|4500) drop' "$RULES"; then
	_t_fail "IPsec ports stay open for the rest of the LAN"
else
	_t_pass "IPsec ports stay open for the rest of the LAN"
fi
warp_line=$(grep -n '@warp_v4 drop' "$RULES" | cut -d: -f1)
if [[ -n $warp_line && -n $accept_line ]] && ((warp_line < accept_line)); then
	_t_pass "the WARP drop precedes the forward accept"
else
	_t_fail "the WARP drop precedes the forward accept"
fi
_t_file_has "$RULES" 'iifname "docker0" accept' "docker forwarding is untouched by gateway mode"
if command -v nft >/dev/null 2>&1 && nft -c -f "$RULES" >/dev/null 2>&1; then
	_t_pass "nft -c accepts the gateway ruleset"
else
	printf '  (skipped: nft -c not permitted here)\n'
fi
ALLOW_LAN_GATEWAY="false"

_t_report "test_wg_firewall.sh"

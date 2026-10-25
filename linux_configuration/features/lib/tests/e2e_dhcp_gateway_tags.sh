#!/usr/bin/env bash
# End-to-end check that gateway mode's DHCP config hands out the right router.
#
#   sudo linux_configuration/features/lib/tests/e2e_dhcp_gateway_tags.sh
#
# Deliberately NOT named test_*.sh: it needs root and real network namespaces.
# A real dnsmasq serves leases inside one namespace, a real dhcpcd asks for one
# from another, over a veth pair -- the host LAN and its dnsmasq are never
# touched. It proves what a unit test cannot: that the TAGGED router options in
# lan-gateway.conf beat the untagged one in lan-dhcp.conf, for a normal client
# AND for an exempt MAC.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly NS_S="gwtag-srv" NS_C="gwtag-cli"
readonly PC_IP="10.99.0.43" FUNBOX="10.99.0.1"
TMP="$(mktemp -d)"

drop_namespaces() {
	ip netns pids "$NS_S" 2>/dev/null | xargs -r kill 2>/dev/null || true
	ip netns pids "$NS_C" 2>/dev/null | xargs -r kill 2>/dev/null || true
	ip netns del "$NS_S" 2>/dev/null || true
	ip netns del "$NS_C" 2>/dev/null || true
}
trap 'drop_namespaces; rm -rf "$TMP"' EXIT

# shellcheck source=../dns_gateway.sh
. "$SCRIPT_DIR/../dns_gateway.sh"

drop_namespaces
ip netns add "$NS_S"
ip netns add "$NS_C"
ip link add gwt-s netns "$NS_S" type veth peer name gwt-c netns "$NS_C"
ip -n "$NS_S" addr add "${PC_IP}/24" dev gwt-s
ip -n "$NS_S" link set gwt-s up
ip -n "$NS_C" link set gwt-c up

# The untagged router mirrors lan-dhcp.conf; the gateway conf is the real render.
cat >"$TMP/dhcp.conf" <<EOF
port=0
interface=gwt-s
dhcp-range=10.99.0.10,10.99.0.20,2h
dhcp-option=option:router,${FUNBOX}
dhcp-leasefile=${TMP}/leases
EOF
LAN_IP="$PC_IP" GATEWAY="$FUNBOX" render_gateway_dnsmasq_conf "$TMP/gateway.conf"
ip netns exec "$NS_S" dnsmasq --conf-file="$TMP/dhcp.conf" \
	--conf-file="$TMP/gateway.conf" --pid-file="$TMP/dnsmasq.pid"

# Router a client with <mac> is offered, as dhcpcd's test mode reports it.
router_for() {
	ip -n "$NS_C" link set gwt-c down
	ip -n "$NS_C" link set gwt-c address "$1"
	ip -n "$NS_C" link set gwt-c up
	ip netns exec "$NS_C" timeout 20 dhcpcd -4 -T -t 15 gwt-c 2>/dev/null |
		awk -F= '/^new_routers=/{gsub(/\x27/,"",$2); print $2; exit}'
}

status=0
check() {
	if [[ $2 == "$3" ]]; then
		printf '  OK: %s (%s)\n' "$1" "$2"
	else
		printf '  FAIL: %s (want %s, got %s)\n' "$1" "$3" "${2:-<none>}"
		status=1
	fi
}
check "a normal client is routed through the PC" "$(router_for 02:00:00:00:00:01)" "$PC_IP"
check "an exempt client keeps the Funbox" "$(router_for "${GATEWAY_EXEMPT_MACS[0]}")" "$FUNBOX"
exit "$status"

#!/usr/bin/env bash
# End-to-end check that gateway mode's forward rules stop the WARP tunnel and
# nothing else.
#
#   sudo linux_configuration/features/lib/tests/e2e_warp_forward_drop.sh
#
# Deliberately NOT named test_*.sh: it needs root and real network namespaces.
# The real lan_gateway_set/lan_gateway_forward render is loaded into a router
# namespace that hairpins on one NIC, like the PC on the LAN. A client sends
# real packets through it, and nft counters in an "internet" namespace record
# what got past. The host's own ruleset is never touched.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly NS_B="warpe-br" NS_C="warpe-cli" NS_R="warpe-rtr" NS_I="warpe-inet"
readonly CLI_IP="10.98.0.21" RTR_IP="10.98.0.43" INET_IP="10.98.0.1"
# WireGuard and MASQUE ingress, a proxied site in consumer-WARP anycast space,
# and an ordinary host.
readonly WG="162.159.193.9" MASQUE="162.159.197.4" SHARED="188.114.96.3" PLAIN="93.184.215.14"

drop_namespaces() {
	local ns
	for ns in "$NS_B" "$NS_C" "$NS_R" "$NS_I"; do
		ip netns del "$ns" 2>/dev/null || true
	done
}
trap drop_namespaces EXIT

die() {
	printf '%s\n' "$1" >&2
	exit 1
}
# shellcheck source=../wg_gateway.sh
. "$SCRIPT_DIR/../wg_gateway.sh"

drop_namespaces
for ns in "$NS_B" "$NS_C" "$NS_R" "$NS_I"; do ip netns add "$ns"; done
ip -n "$NS_B" link add br0 type bridge
ip -n "$NS_B" link set br0 up
# One veth per host, all on the bridge: a single LAN segment. <port> names the
# bridge end; every host end is lan0.
attach() {
	ip link add lan0 netns "$1" type veth peer name "$2" netns "$NS_B"
	ip -n "$NS_B" link set "$2" master br0 up
	ip -n "$1" addr add "$3/24" dev lan0
	ip -n "$1" link set lan0 up
}
attach "$NS_C" p-cli "$CLI_IP"
attach "$NS_R" p-rtr "$RTR_IP"
attach "$NS_I" p-inet "$INET_IP"

ip -n "$NS_C" route add default via "$RTR_IP"
ip -n "$NS_R" route add default via "$INET_IP"
ip netns exec "$NS_R" sysctl -qw net.ipv4.ip_forward=1 net.ipv4.conf.all.send_redirects=0 \
	net.ipv4.conf.lan0.send_redirects=0
for ip in "$WG" "$MASQUE" "$SHARED" "$PLAIN"; do ip -n "$NS_I" addr add "$ip/32" dev lan0; done

LAN_IFACE="lan0" LAN_IP="$RTR_IP" LAN_SUBNET="10.98.0.0/24" ALLOW_LAN_GATEWAY="true"
ip netns exec "$NS_R" nft -f - <<EOF
table inet filter {
$(lan_gateway_set)
	chain forward {
		type filter hook forward priority filter; policy drop;
$(lan_gateway_forward)
	}
}
EOF

# One counter per probe, so each verdict is read on its own.
readonly PROBES="udp:$WG:2408 tcp:$MASQUE:443 udp:$MASQUE:443 udp:$SHARED:443 \
tcp:$SHARED:443 udp:$PLAIN:4500 tcp:$PLAIN:443"
{
	printf 'table inet seen {\n\tchain input {\n\t\ttype filter hook input priority filter;\n'
	for p in $PROBES; do
		IFS=: read -r proto ip port <<<"$p"
		printf '\t\tip daddr %s %s dport %s counter comment "%s"\n' "$ip" "$proto" "$port" "$p"
	done
	printf '\t}\n}\n'
} | ip netns exec "$NS_I" nft -f -

for p in $PROBES; do
	IFS=: read -r proto ip port <<<"$p"
	ip netns exec "$NS_C" timeout 2 bash -c "echo x >/dev/$proto/$ip/$port" 2>/dev/null || true
done

seen() {
	ip netns exec "$NS_I" nft list chain inet seen input |
		awk -v c="\"$1\"" '$0 ~ c {for(i=1;i<=NF;i++) if($i=="packets") n=$(i+1)} END {print n}'
}
status=0
check() {
	local got
	got="$(seen "$2")"
	if [[ $1 == blocked && $got == 0 ]] || [[ $1 == passes && ${got:-0} -gt 0 ]]; then
		printf '  OK: %s %s (%s packets)\n' "$2" "$1" "$got"
	else
		printf '  FAIL: %s should be %s (%s packets)\n' "$2" "$1" "${got:-<none>}"
		status=1
	fi
}
check blocked "udp:$WG:2408"
check blocked "tcp:$MASQUE:443"
check blocked "udp:$MASQUE:443"
check blocked "udp:$SHARED:443"
check passes "tcp:$SHARED:443"
check passes "udp:$PLAIN:4500"
check passes "tcp:$PLAIN:443"

# The window (warp_window.sh open): one catch-all element with a timeout lets
# WARP through, and the kernel closes it again when the timeout runs out.
probe() {
	local before
	before="$(seen "udp:$WG:2408")"
	ip netns exec "$NS_C" bash -c "echo x >/dev/udp/$WG/2408" 2>/dev/null || true
	printf '%s\n' "$(($(seen "udp:$WG:2408") - before))"
}
window() {
	if [[ $2 == "$3" ]]; then
		printf '  OK: %s\n' "$1"
	else
		printf '  FAIL: %s (want %s packets, got %s)\n' "$1" "$3" "$2"
		status=1
	fi
}
ip netns exec "$NS_R" nft add element inet filter warp_open '{ 0.0.0.0/0 timeout 3s }'
window "an open window lets WARP through" "$(probe)" 1
sleep 4
window "the window closes itself when its timeout runs out" "$(probe)" 0
exit "$status"

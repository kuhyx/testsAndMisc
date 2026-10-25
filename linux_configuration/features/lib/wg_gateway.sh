#!/bin/bash
# LAN gateway rules (setup_dns_blocker.sh gateway): forward other devices'
# traffic, force their DNS to the blocker, drop DoH, DoT and the WARP tunnel.
#
# Sourced by wg_firewall.sh, which renders the result into /etc/nftables.conf,
# so a reboot or any other allow-* apply keeps it. Only FORWARDED traffic and
# the nat hooks are touched: the PC's own traffic never passes through these.

# DoH/DoT provider addresses. Everything else to these from the LAN is dropped,
# so a browser set to "secure DNS" fails over to plain DNS, which is DNATed to
# the blocker. The PC's own upstream queries are OUTPUT, never FORWARD.
readonly DOH_RESOLVERS_V4="1.1.1.1, 1.0.0.1, 8.8.8.8, 8.8.4.4, 9.9.9.9, 149.112.112.112, \
208.67.222.222, 208.67.220.220, 94.140.14.14, 94.140.15.15, 45.90.28.0/24, \
45.90.30.0/24, 76.76.2.0/24, 76.76.10.0/24, 194.242.2.0/24, 185.228.168.9, \
185.228.169.9, 104.16.248.249, 104.16.249.249, 162.159.36.1, 162.159.46.1"

# Cloudflare WARP tunnel ingress. A WARP client tunnels everything past the
# DNS redirect, so the tunnel itself is the bypass. Dedicated ranges are dropped
# outright (MASQUE falls back to TCP 443, so a port match is not enough):
# 162.159.193.0/24 WireGuard, 162.159.197.0/24 MASQUE, 162.159.192.0/24 the
# consumer endpoint. Source: developers.cloudflare.com/cloudflare-one/
# team-and-resources/devices/warp/deployment/firewall/ (2026-10-25).
readonly WARP_V4="162.159.192.0/24, 162.159.193.0/24, 162.159.197.0/24"
# Consumer WARP endpoints that share anycast space with proxied websites: only
# UDP is dropped there, so those sites still load (HTTP/3 falls back to TCP).
# No LAN-wide drop of UDP 500/1701/4500: that would break IPsec for everyone.
readonly WARP_UDP_V4="162.159.192.0/22, 162.159.204.0/22, 188.114.96.0/22"
# Sources in warp_open skip both WARP drops. Empty by default; warp_window.sh
# fills it Mon/Fri 09:00-15:30 with an element that times out by itself. Any
# re-apply of this ruleset empties it again.

# Fill in LAN_IFACE/LAN_IP from the default route unless the caller set them.
lan_gateway_detect() {
	local route
	[[ -n ${LAN_IFACE:-} && -n ${LAN_IP:-} ]] && return 0
	route="$(ip -4 route get 1.1.1.1 2>/dev/null || true)"
	LAN_IFACE="$(awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}' <<<"$route")"
	LAN_IP="$(awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' <<<"$route")"
	[[ -n $LAN_IFACE && -n $LAN_IP ]] || die "Could not detect the LAN interface/IP."
}

# Fragments for render_nftables_ruleset. Each prints nothing while gateway
# mode is off -- except the nat table, whose declare+delete is always rendered
# so that turning gateway mode off removes a stale table too.
lan_gateway_on() { [[ ${ALLOW_LAN_GATEWAY:-false} == "true" ]]; }

# One interval set of IPv4 ranges, inside table inet filter.
_lan_gateway_v4_set() {
	printf '\n\tset %s {\n\t\ttype ipv4_addr\n\t\tflags interval\n' "$1"
	printf '\t\telements = { %s }\n\t}\n' "$2"
}

# The DoH and WARP address sets.
lan_gateway_set() {
	lan_gateway_on || return 0
	_lan_gateway_v4_set doh_v4 "$DOH_RESOLVERS_V4"
	_lan_gateway_v4_set warp_v4 "$WARP_V4"
	_lan_gateway_v4_set warp_udp_v4 "$WARP_UDP_V4"
	printf '\n\tset warp_open {\n\t\ttype ipv4_addr\n\t\tflags interval,timeout\n\t}\n'
}

# Forward-chain rules, placed first in the chain: the drops before the accept.
lan_gateway_forward() {
	lan_gateway_on || return 0
	lan_gateway_detect
	local from="iifname \"${LAN_IFACE}\" ip saddr ${LAN_SUBNET}"
	printf '\n\t\t%s ip daddr @doh_v4 drop' "$from"
	printf '\n\t\t%s tcp dport 853 drop' "$from"
	printf '\n\t\t%s udp dport 853 drop' "$from"
	printf '\n\t\t%s ip saddr != @warp_open ip daddr @warp_v4 drop' "$from"
	printf '\n\t\t%s ip saddr != @warp_open ip daddr @warp_udp_v4 meta l4proto udp drop' "$from"
	printf '\n\t\tiifname "%s" oifname "%s" ip saddr %s accept' \
		"$LAN_IFACE" "$LAN_IFACE" "$LAN_SUBNET"
}

lan_gateway_table() {
	printf 'table ip lan_gateway\ndelete table ip lan_gateway\n'
	lan_gateway_on || return 0
	lan_gateway_detect
	local dns="iifname \"${LAN_IFACE}\" ip saddr ${LAN_SUBNET} ip saddr != ${LAN_IP} ip daddr != ${LAN_IP}"
	cat <<EOF

table ip lan_gateway {
	chain prerouting {
		type nat hook prerouting priority dstnat; policy accept;
		${dns} udp dport 53 dnat to ${LAN_IP}
		${dns} tcp dport 53 dnat to ${LAN_IP}
	}
	chain postrouting {
		type nat hook postrouting priority srcnat; policy accept;
		oifname "${LAN_IFACE}" ip saddr ${LAN_SUBNET} ip saddr != ${LAN_IP} ip daddr != ${LAN_SUBNET} masquerade
	}
}
EOF
}

allow_lan_gateway() {
	export ALLOW_LAN_GATEWAY=true
	save_config
	write_nftables_ruleset
	verify_nftables_then_apply
	log_ok "LAN gateway rules applied: forwarding, DNS redirect, DoH/DoT and WARP drop (persisted)."
}

deny_lan_gateway() {
	export ALLOW_LAN_GATEWAY=false
	save_config
	write_nftables_ruleset
	verify_nftables_then_apply
	log_ok "LAN gateway rules removed (persisted)."
}

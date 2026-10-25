#!/bin/bash
# Gateway mode: other LAN devices route through this PC, so their DNS can be
# forced to the blocker and DoH/DoT dropped, instead of merely suggested.
#
# Sourced by setup_dns_blocker.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode.
#
# The PC's OWN connectivity never changes: static IP, default route via the
# Funbox, firewall output policy accept. Only DHCP clients route through it.
# Known limit: one NIC on the same L2 as the Funbox, so a device set by hand
# to gateway or DNS 192.168.1.1 still bypasses this. Recovery steps live in
# docs/DOCS-lan-blocker-contingency.md.

GATEWAY_CONF="/etc/dnsmasq.d/lan-gateway.conf"
GATEWAY_SYSCTL="/etc/sysctl.d/90-lan-gateway.conf"
GATEWAY_DOCKER_UNIT="/etc/systemd/system/lan-gateway-docker-forward.service"
# Devices that keep the Funbox as gateway, so a dead PC takes down less:
# nextcloud-pi and the P110 smart plug.
readonly GATEWAY_EXEMPT_MACS=(2c:cf:67:1e:35:3a 58:04:4f:db:c9:e8)

# Tagged options beat the untagged router in lan-dhcp.conf, and every client
# matches exactly one of the two tags, so lan-dhcp.conf needs no edit.
render_gateway_dnsmasq_conf() {
	local target="$1" mac
	{
		printf '# Managed by setup_dns_blocker.sh gateway -- remove with gateway-off.\n'
		for mac in "${GATEWAY_EXEMPT_MACS[@]}"; do
			printf 'dhcp-host=%s,set:direct\n' "$mac"
		done
		printf 'dhcp-option=tag:!direct,option:router,%s\n' "$LAN_IP"
		printf 'dhcp-option=tag:direct,option:router,%s\n' "$GATEWAY"
	} >"$target"
}

render_gateway_sysctl() {
	cat >"$1" <<EOF
# Managed by setup_dns_blocker.sh gateway.
net.ipv4.ip_forward = 1
# One NIC on the Funbox's L2: with redirects on, the kernel tells each client
# "go straight to ${GATEWAY}" and gateway mode silently does nothing.
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.${LAN_IFACE}.send_redirects = 0
EOF
}

# Docker sets the legacy iptables FORWARD policy to DROP, and that hook vetoes
# whatever nftables accepts. DOCKER-USER is the chain Docker leaves to us, but
# it does not survive a reboot, so a unit re-inserts it whenever docker starts.
render_docker_user_unit() {
	local rule="DOCKER-USER -i ${LAN_IFACE} -o ${LAN_IFACE} -j ACCEPT"
	cat >"$1" <<EOF
[Unit]
Description=Let LAN gateway traffic past Docker's FORWARD DROP
After=docker.service
PartOf=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'iptables -C ${rule} 2>/dev/null || iptables -I ${rule}'
ExecStop=/bin/sh -c 'iptables -D ${rule} 2>/dev/null || true'

[Install]
WantedBy=docker.service
EOF
}

# Probes, separate so the self-check can be tested without a network.
pc_route() { ip -4 route get 1.1.1.1 2>/dev/null || true; }
pc_ping() { ping -c1 -W3 1.1.1.1 >/dev/null 2>&1; }
pc_resolve() { timeout 10 getent hosts example.com >/dev/null 2>&1; }
blocker_answers() {
	local ans
	ans="$(dig +short +time=3 +tries=2 @"${LAN_IP}" example.com 2>/dev/null | head -1)"
	[[ -n $ans && $ans != "0.0.0.0" ]]
}

# The PC itself must stay online; nothing else gateway mode does matters more.
gateway_self_check() {
	local route
	route="$(pc_route)"
	[[ $route == *"via ${GATEWAY} dev ${LAN_IFACE}"* ]] || {
		log_error "self-check: PC default route is not via ${GATEWAY}: ${route}"
		return 1
	}
	pc_ping || {
		log_error "self-check: PC cannot reach 1.1.1.1"
		return 1
	}
	pc_resolve || {
		log_error "self-check: PC cannot resolve example.com"
		return 1
	}
	blocker_answers || {
		log_error "self-check: the blocker at ${LAN_IP} does not answer"
		return 1
	}
}

apply_or_rollback() {
	if gateway_self_check; then
		return 0
	fi
	log_error "Self-check failed -- rolling gateway mode back."
	cmd_gateway_off
	die "Gateway mode rolled back; the PC keeps its own connection."
}

cmd_gateway() {
	detect_lan
	[[ -f $DHCP_CONF ]] ||
		die "Gateway mode needs DHCP mode (the PC hands out the gateway): run 'dhcp' first."
	firewall_is_loaded ||
		die "Gateway mode needs the default-drop firewall from setup_wireguard_ssh.sh."
	gateway_self_check || die "The PC is not healthy BEFORE the change -- fix that first."

	render_gateway_sysctl "$GATEWAY_SYSCTL"
	sysctl -q -p "$GATEWAY_SYSCTL"
	render_docker_user_unit "$GATEWAY_DOCKER_UNIT"
	systemctl daemon-reload
	systemctl enable lan-gateway-docker-forward.service
	if is_service_active docker; then
		systemctl restart lan-gateway-docker-forward.service
	fi
	bash "$WG_SCRIPT" allow-lan-gateway
	write_dhcp_conf # re-rendered for the shorter DHCP_LEASE
	render_gateway_dnsmasq_conf "$GATEWAY_CONF"
	if ! dnsmasq --test >/dev/null 2>&1; then
		rm -f "$GATEWAY_CONF"
		die "dnsmasq rejected the gateway config -- removed it."
	fi
	systemctl restart dnsmasq
	apply_or_rollback
	log_ok "Gateway mode ON: new leases route through ${LAN_IP}; DNS forced, DoH/DoT dropped."
	log_info "Devices switch at their next lease renewal; toggle WiFi to switch now."
	log_info "Undo: sudo ${SELF} gateway-off   (see docs/DOCS-lan-blocker-contingency.md)"
}

# Hand the Funbox back as everyone's gateway. DNS blocking and DHCP stay on.
cmd_gateway_off() {
	detect_lan
	rm -f "$GATEWAY_CONF"
	is_service_active dnsmasq && systemctl restart dnsmasq
	bash "$WG_SCRIPT" deny-lan-gateway
	systemctl disable --now lan-gateway-docker-forward.service 2>/dev/null || true
	rm -f "$GATEWAY_DOCKER_UNIT" "$GATEWAY_SYSCTL"
	systemctl daemon-reload
	log_ok "Gateway mode OFF: new leases name ${GATEWAY} as the gateway again."
	log_warn "Devices still on an old lease: toggle their WiFi to get internet back."
}

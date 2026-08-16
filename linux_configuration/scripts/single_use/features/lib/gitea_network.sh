#!/bin/bash
# Firewall, UPnP and router guidance for exposing Gitea.
#
# Sourced by setup_gitea.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

open_firewall() {
	if [[ -x $WIREGUARD_SCRIPT ]]; then
		sudo "$WIREGUARD_SCRIPT" allow-web
	else
		log_warn "Could not find ${WIREGUARD_SCRIPT} -- open tcp/80 and tcp/443 manually."
	fi
}

attempt_upnp() {
	has_cmd upnpc || {
		log_warn "upnpc not installed -- skipping automatic port-forward attempt."
		return 0
	}
	local lan_ip
	lan_ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
	[[ -n $lan_ip ]] || {
		log_warn "Could not detect LAN IP -- skipping UPnP."
		return 0
	}
	if upnpc -e "gitea-https" -a "$lan_ip" 443 443 tcp >/dev/null 2>&1 &&
		upnpc -e "gitea-http" -a "$lan_ip" 80 80 tcp >/dev/null 2>&1; then
		log_ok "UPnP port mapping succeeded for 80 and 443 -> ${lan_ip}."
	else
		log_warn "UPnP port mapping failed or unsupported by your router."
	fi
}

print_router_instructions() {
	local lan_ip
	lan_ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
	cat <<EOF

=== Manual step: verify port forwarding on your router (cannot be automated) ===
1. Log into your router admin page (often http://192.168.1.1).
2. Find "Port Forwarding" / "Virtual Server" / "NAT" settings.
3. Forward TCP 80 -> ${lan_ip}:80 and TCP 443 -> ${lan_ip}:443.
4. Save (and reboot the router if it requires it).
5. Confirm from OUTSIDE your LAN (e.g. phone on cellular data):
     https://${GITEA_DOMAIN}
EOF
}

status_cmd() {
	echo "=== Containers ==="
	docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || echo "(not deployed)"
	echo
	echo "=== Caddy certificate ==="
	docker logs gitea-caddy 2>&1 | grep -i "certificate obtained" | tail -3 || echo "(no certificate log entry yet)"
}

usage() {
	cat <<EOF
Usage: $0 <command>

Commands:
  setup    Full first-time setup (idempotent, safe to re-run).
  status   Show container and certificate status.
  help     Show this message.
EOF
}

#!/bin/bash
# Self-hosted Gitea git server, mirroring GitHub repos, exposed publicly via
# DuckDNS + Caddy automatic HTTPS.
#
# Companion to setup_wireguard_ssh.sh, which owns /etc/nftables.conf and
# provides the 'allow-web' firewall rule this script depends on.
#
# DNS note: kuhy.duckdns.org is kept updated by an existing cron job installed
# by install_joplin.sh (~/.joplin-server/duckdns-update.sh) -- this script
# does not manage DuckDNS itself.
#
# Networking note: Gitea and Caddy run with `network_mode: host`, not a
# Docker bridge network. This host's custom nftables ruleset has a
# default-drop FORWARD chain with no rules; Docker's own forwarding rules
# (separate iptables-legacy tables) don't override it, since both hook the
# same netfilter point and a DROP verdict from either is terminal. That
# silently blocks all bridge-networked container egress -- breaking both
# Caddy's ACME renewal and Gitea's GitHub pull-mirroring. Host networking
# sidesteps the FORWARD chain entirely (uses INPUT/OUTPUT only, both already
# permissive) without touching the shared firewall script. Gitea binds to
# 127.0.0.1:3000 only -- never exposed directly, only reachable via Caddy.
#
# Usage:
#   ./setup_gitea.sh setup    - full first-time setup (idempotent, re-runnable)
#   ./setup_gitea.sh status   - show container + certificate status
#   ./setup_gitea.sh help

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

readonly GITEA_DOMAIN="kuhy.duckdns.org"
readonly GITEA_ADMIN_USER="kuhyx"
readonly GITEA_ADMIN_EMAIL="krzysztofrudnicki0@gmail.com"
readonly GITEA_DATA_DIR="${HOME}/gitea"
readonly COMPOSE_FILE="${GITEA_DATA_DIR}/docker-compose.yml"
readonly CADDYFILE="${GITEA_DATA_DIR}/Caddyfile"
readonly ADMIN_PASSWORD_FILE="${GITEA_DATA_DIR}/.admin_password"
readonly ADMIN_TOKEN_FILE="${GITEA_DATA_DIR}/.admin_token"
readonly WIREGUARD_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"

die() {
	log_error "$1"
	exit 1
}

write_compose_files() {
	ensure_dir "$GITEA_DATA_DIR"
	cat >"$COMPOSE_FILE" <<EOF
services:
  gitea:
    image: gitea/gitea:1.22.3
    container_name: gitea
    restart: unless-stopped
    network_mode: host
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__database__DB_TYPE=sqlite3
      - GITEA__server__DOMAIN=${GITEA_DOMAIN}
      - GITEA__server__ROOT_URL=https://${GITEA_DOMAIN}/
      - GITEA__server__HTTP_ADDR=127.0.0.1
      - GITEA__server__HTTP_PORT=3000
      - GITEA__server__DISABLE_SSH=true
      - GITEA__service__DISABLE_REGISTRATION=true
      - GITEA__service__REGISTER_EMAIL_CONFIRM=false
      - GITEA__security__INSTALL_LOCK=true
      - GITEA__mirror__ENABLED=true
      - GITEA__mirror__DEFAULT_INTERVAL=10m
      - GITEA__mirror__MIN_INTERVAL=10m
    volumes:
      - ./gitea-data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro

  caddy:
    image: caddy:2.8
    container_name: gitea-caddy
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config

volumes:
  caddy-data:
  caddy-config:
EOF

	cat >"$CADDYFILE" <<EOF
${GITEA_DOMAIN} {
	reverse_proxy 127.0.0.1:3000
}
EOF
	log_ok "Wrote ${COMPOSE_FILE} and ${CADDYFILE}."
}

start_containers() {
	docker compose -f "$COMPOSE_FILE" up -d
}

wait_for_gitea() {
	log_info "Waiting for Gitea to become ready..."
	local attempt logs
	for ((attempt = 1; attempt <= 60; attempt++)); do
		# Capture into a variable rather than piping straight into
		# `grep -q`: grep quits at the first match, SIGPIPE-ing `docker
		# logs` before it finishes writing, and under `pipefail` that
		# upstream non-zero exit clobbers grep's own success -- the `if`
		# never sees a match even though one is right there in the log.
		logs=$(docker logs gitea 2>&1)
		if grep -q "Listen: http" <<<"$logs"; then
			log_ok "Gitea is ready."
			return 0
		fi
		sleep 2
	done
	die "Gitea did not become ready within 2 minutes -- check 'docker logs gitea'."
}

bootstrap_admin() {
	if docker exec -u git gitea gitea admin user list 2>/dev/null | grep -q "$GITEA_ADMIN_USER"; then
		log_info "Admin user '${GITEA_ADMIN_USER}' already exists -- not recreating."
		return 0
	fi
	umask 077
	openssl rand -base64 24 >"$ADMIN_PASSWORD_FILE"
	chmod 600 "$ADMIN_PASSWORD_FILE"
	docker exec -u git gitea gitea admin user create \
		--username "$GITEA_ADMIN_USER" --password "$(cat "$ADMIN_PASSWORD_FILE")" \
		--email "$GITEA_ADMIN_EMAIL" --admin --must-change-password=false
	log_ok "Created admin user '${GITEA_ADMIN_USER}'. Password saved to ${ADMIN_PASSWORD_FILE} (chmod 600)."
}

mint_api_token() {
	if [[ -f $ADMIN_TOKEN_FILE ]]; then
		log_info "API token already exists at ${ADMIN_TOKEN_FILE} -- not regenerating."
		return 0
	fi
	umask 077
	docker exec -u git gitea gitea admin user generate-access-token \
		--username "$GITEA_ADMIN_USER" --token-name automation --scopes all --raw >"$ADMIN_TOKEN_FILE"
	chmod 600 "$ADMIN_TOKEN_FILE"
	log_ok "API token saved to ${ADMIN_TOKEN_FILE} (chmod 600)."
}

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

main() {
	local cmd="${1:-help}"
	case "$cmd" in
	setup)
		write_compose_files
		start_containers
		wait_for_gitea
		bootstrap_admin
		mint_api_token
		open_firewall
		attempt_upnp
		print_router_instructions
		log_ok "Gitea setup complete."
		;;
	status)
		status_cmd
		;;
	help | -h | --help)
		usage
		;;
	*)
		log_error "Unknown command: $cmd"
		usage
		exit 1
		;;
	esac
}

main "$@"

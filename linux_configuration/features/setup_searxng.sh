#!/bin/bash
#
# setup_searxng.sh — SearXNG metasearch at searx.kuhy.duckdns.org
#
# Runs a private SearXNG instance behind the existing shared Caddy edge
# (gitea-caddy), configured to earn an A+ Mozilla Observatory grade while
# staying "Vanilla" (settings-only changes — no template or static-file edits).
#
# No DuckDNS work is needed: DuckDNS wildcards *.kuhy.duckdns.org, so adding the
# Caddy snippet is enough to get a certificate.
#
# What it does (idempotent — safe to re-run):
#   - Installs runtime deps.
#   - Writes ~/searxng/{docker-compose.yml,core-config/settings.yml}.
#   - Runs valkey (limiter backend) on 127.0.0.1:6379.
#   - Runs searxng on 127.0.0.1:8090, both with network_mode: host.
#   - Adds a reverse-proxy + security-header snippet to the shared edge.
#   - Opens the firewall via setup_wireguard_ssh.sh (already open in practice).
#
# Why network_mode: host — this host's nftables ruleset has
# `chain forward { policy drop; }` with no accept rules, and a DROP at
# NF_INET_FORWARD is terminal regardless of Docker's own legacy-iptables
# ACCEPTs. Docker BRIDGE networking therefore has zero outbound access here, so
# a stock bridge-network SearXNG cannot reach a single search engine. Host
# networking sidesteps the FORWARD chain entirely. The cost is that there is no
# bridge isolation left, so both containers are pinned to loopback explicitly
# and that binding is asserted before the site is published.
#
# Reboot survival: containers use restart: unless-stopped and docker.service is
# enabled — no systemd unit is needed.
#
# Usage:
#   setup_searxng.sh [setup]   Deploy (default).
#   setup_searxng.sh status    Self-diagnose the deployment.
#   setup_searxng.sh help      Show this help.
#
# Prerequisite: setup_gitea.sh must have been run at least once (the gitea-caddy
# edge must exist). Run as your normal user, not root.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

# --- Configuration ----------------------------------------------------------
readonly SEARX_DOMAIN="searx.kuhy.duckdns.org"
# 8080 is granian's default AND is already taken on this host, so it is set
# explicitly rather than left alone.
readonly SEARX_PORT="8090"
readonly VALKEY_PORT="6379"
# searxng/searxng:latest as of 2026-08-09 == release 2026.8.4. See the comment
# on the image: line in the compose heredoc for why this is pinned.
readonly SEARX_IMAGE="searxng/searxng@sha256:f4c8e59de166ed71f6380c0847c312ca51f0d41996e31d0559163b6b09ecde52"
readonly SEARX_DATA_DIR="${HOME}/searxng"
readonly SEARX_COMPOSE="${SEARX_DATA_DIR}/docker-compose.yml"
readonly SEARX_CONFIG_DIR="${SEARX_DATA_DIR}/core-config"
readonly SEARX_SETTINGS="${SEARX_CONFIG_DIR}/settings.yml"
readonly SEARX_LIMITER="${SEARX_CONFIG_DIR}/limiter.toml"
# Shared edge owned by setup_gitea.sh.
readonly GITEA_DATA_DIR="${HOME}/gitea"
readonly SITES_DIR="${GITEA_DATA_DIR}/sites"
readonly SEARX_SNIPPET="${SITES_DIR}/searx.caddy"
readonly CADDY_CONTAINER="gitea-caddy"
readonly SEARX_CONTAINER="searxng"
readonly VALKEY_CONTAINER="searxng-valkey"
# Sibling script (single source of truth for the firewall).
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"

die() {
	log_error "$1"
	exit 1
}

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit "${1:-0}"
}

# --- Phase 1: preflight -----------------------------------------------------
port_in_use() {
	local port="$1"
	ss -ltn 2>/dev/null | grep -qE "[:.]${port}[[:space:]]"
}

# A port held by one of OUR OWN containers is a re-run, not a conflict. Only a
# foreign holder is fatal, otherwise the second `setup` run can never succeed.
port_held_by_us() {
	local port="$1" name pid listeners
	for name in "$SEARX_CONTAINER" "$VALKEY_CONTAINER"; do
		pid="$(docker inspect -f '{{.State.Pid}}' "$name" 2>/dev/null || echo "")"
		[[ -n $pid && $pid != "0" ]] || continue
		listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"
		if grep -qE "[:.]${port}[[:space:]]" <<<"$listeners"; then
			return 0
		fi
	done
	return 1
}

preflight() {
	[[ ${EUID} -ne 0 ]] || die "Run as your normal user, not root."
	install_missing_pacman_packages docker docker-compose openssl curl
	is_service_active docker || die "docker.service is not running."
	docker ps --format '{{.Names}}' | grep -qx "$CADDY_CONTAINER" ||
		die "The ${CADDY_CONTAINER} edge is not running — run setup_gitea.sh first."

	local port
	for port in "$SEARX_PORT" "$VALKEY_PORT"; do
		if port_in_use "$port" && ! port_held_by_us "$port"; then
			die "Port ${port} is already in use by something else. Free it or change the port."
		fi
	done
	log_ok "Preflight passed (edge up, ports ${SEARX_PORT}/${VALKEY_PORT} available)."
}

# --- Phase 2: write the stack -----------------------------------------------
# Regenerating secret_key on every run would invalidate every image-proxy HMAC
# and every stored preference cookie, so an existing one is reused. openssl,
# not an inline python heredoc (house shell rule).
read_or_make_secret() {
	local existing=""
	if [[ -f $SEARX_SETTINGS ]]; then
		existing="$(grep -oP '^\s*secret_key:\s*"\K[^"]+' "$SEARX_SETTINGS" 2>/dev/null || true)"
	fi
	if [[ -n $existing ]]; then
		printf '%s' "$existing"
	else
		openssl rand -hex 32
	fi
}

# The container entrypoint chowns core-config/ and settings.yml to its own
# searxng user (uid 977), after which this script's own user can no longer
# overwrite them — so a second `setup` run dies with "Permission denied" unless
# ownership is reclaimed first. Idempotence is the whole point of this script,
# so reclaim rather than skip.
reclaim_config_ownership() {
	local target
	for target in "$SEARX_CONFIG_DIR" "$SEARX_SETTINGS" "$SEARX_LIMITER"; do
		[[ -e $target ]] || continue
		[[ -O $target ]] && continue
		if ! sudo -n chown "$(id -u):$(id -g)" "$target" 2>/dev/null; then
			die "${target} is owned by the container (uid 977) and passwordless sudo is unavailable. Run: sudo chown -R $(id -u):$(id -g) ${SEARX_CONFIG_DIR}"
		fi
		log_info "Reclaimed ownership of ${target} from the container."
	done
}

# shellcheck source=lib/searxng_stack.sh
source "$SCRIPT_DIR/lib/searxng_stack.sh"
# shellcheck source=lib/searxng_settings.sh
source "$SCRIPT_DIR/lib/searxng_settings.sh"
# shellcheck source=lib/searxng_limiter.sh
source "$SCRIPT_DIR/lib/searxng_limiter.sh"
# shellcheck source=lib/searxng_start.sh
source "$SCRIPT_DIR/lib/searxng_start.sh"
# shellcheck source=lib/searxng_expose.sh
source "$SCRIPT_DIR/lib/searxng_expose.sh"
# shellcheck source=lib/searxng_status.sh
source "$SCRIPT_DIR/lib/searxng_status.sh"


main() {
	local cmd="${1:-setup}"
	case "$cmd" in
	setup)
		setup_cmd
		;;
	status)
		status_cmd
		;;
	help | -h | --help)
		usage
		;;
	*)
		log_error "Unknown command: $cmd"
		usage 1
		;;
	esac
}

main "$@"

#!/bin/bash

# ============================================================================
# Expose the existing dnsmasq blocklist over DNS-over-TLS (port 853).
#
# Why this exists:
#   setup_dns_blocker.sh serves the blocklist over plain UDP/53, which only
#   works on the LAN -- and Android's default "Automatic" Private DNS uses DoH
#   and bypasses it entirely. A phone off the LAN gets no filtering at all.
#   Terminating DoT here lets the phone pin Private DNS to a resolver that
#   applies the blocklist, anywhere, with no root and no VPN slot consumed.
#
# Why stunnel rather than Caddy:
#   DoT is a raw TLS stream, not HTTPS. Terminating it in Caddy needs the
#   `layer4` module, which the stock `caddy:2.8` image does not ship -- that
#   would mean an xcaddy rebuild of a container currently serving five live
#   sites. stunnel does exactly this one job, and it can reuse the Let's
#   Encrypt certificate Caddy already renews, so there is no second ACME
#   client competing for port 80.
#
# Usage:
#   ./setup_dot_resolver.sh [--domain <fqdn>] [--check]
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly DEFAULT_DOMAIN="dns.kuhy.duckdns.org"
readonly CADDY_CONTAINER="gitea-caddy"
readonly CERT_DIR="/etc/stunnel/dot"
readonly STUNNEL_CONF="/etc/stunnel/dot-resolver.conf"
readonly SYNC_SCRIPT="/usr/local/bin/sync-dot-cert.sh"
readonly DOT_PORT=853

readonly DEFAULT_BIND="10.8.0.1"

DOMAIN="$DEFAULT_DOMAIN"
# Bind to the WireGuard interface, not 0.0.0.0. An internet-facing DoT
# endpoint is an open resolver: TCP-only so not usable for classic UDP
# amplification, but still someone else's free DNS and a standing attack
# surface. Reaching it over the existing tunnel needs no port-forward and no
# rate limiting, because only configured peers can route to it at all.
BIND_ADDR="$DEFAULT_BIND"
CHECK_ONLY=0

log() { printf '[dot-resolver] %s\n' "$1"; }
die() {
	printf '[dot-resolver] ERROR: %s\n' "$1" >&2
	exit 1
}

usage() {
	cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]
  --domain <fqdn>   DoT hostname (default: $DEFAULT_DOMAIN)
  --bind <addr>     Address to listen on (default: $DEFAULT_BIND, the
                    WireGuard interface). Use 0.0.0.0 only if you intend
                    to expose an open resolver to the internet.
  --check           Verify an existing install, change nothing
  -h, --help        Show this help
EOF
	exit 0
}

require_tools() {
	# Per repo policy a script installs what it needs rather than telling the
	# user to. pacman is non-interactive here; if that fails we stop rather
	# than silently skipping the dependency.
	local missing=()
	command -v stunnel >/dev/null 2>&1 || missing+=(stunnel)
	command -v openssl >/dev/null 2>&1 || missing+=(openssl)
	if [[ ${#missing[@]} -gt 0 ]]; then
		log "Installing: ${missing[*]}"
		sudo pacman -S --needed --noconfirm "${missing[@]}" ||
			die "could not install ${missing[*]}; run: sudo pacman -S ${missing[*]}"
	fi
}

cert_source_dir() {
	# Caddy stores certs per-domain under its data volume.
	printf '/data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/%s' \
		"$DOMAIN"
}

verify_prerequisites() {
	# A DoT endpoint in front of a resolver that is not running would answer
	# every query with a connection error, which looks exactly like a network
	# fault on the phone. Check first.
	ss -lnu 2>/dev/null | grep -qE '127\.0\.0\.1:53' ||
		die "dnsmasq is not listening on 127.0.0.1:53 - run setup_dns_blocker.sh first"

	docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CADDY_CONTAINER" ||
		die "container '$CADDY_CONTAINER' is not running; it owns the certificates"

	local resolved
	resolved="$(getent hosts "$DOMAIN" | awk '{print $1; exit}')" ||
		die "$DOMAIN does not resolve - DuckDNS wildcard missing?"
	log "$DOMAIN resolves to $resolved"

	# Binding to an address that does not exist yet makes stunnel fail at
	# start with an opaque error, so check before installing anything.
	if [[ "$BIND_ADDR" != "0.0.0.0" ]]; then
		ip -brief addr show 2>/dev/null | grep -q "$BIND_ADDR" ||
			die "$BIND_ADDR is not assigned to any interface - is wg0 up?"
		log "Binding to $BIND_ADDR (reachable over WireGuard only)"
	else
		log "WARNING: binding to 0.0.0.0 exposes an open resolver publicly"
	fi
}

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/dot_resolver_install.sh
source "$SCRIPT_DIR/lib/dot_resolver_install.sh"

main() {
	if [[ $CHECK_ONLY -eq 1 ]]; then
		run_check
		exit $?
	fi

	require_tools
	verify_prerequisites
	install_cert_sync
	install_stunnel_conf
	install_units

	log "Syncing certificate..."
	sudo "$SYNC_SCRIPT" || die "certificate sync failed - has Caddy issued $DOMAIN yet?"

	sudo systemctl enable --now stunnel-dot.service
	sudo systemctl enable --now dot-cert-sync.timer
	open_firewall

	log "Done. Point the phone at:"
	log "  Private DNS hostname: $DOMAIN"
	log "And set in phone_focus_mode/config.sh:"
	log "  DNS_TRUSTED_DOT_HOST=\"$DOMAIN\""
	log "  DNS_TRUSTED_DOT_IPS=\"\$(getent hosts $DOMAIN | awk '{print \$1}')\""
	run_check || true
}

while [[ $# -gt 0 ]]; do
	case $1 in
	--domain)
		DOMAIN="$2"
		shift 2
		;;
	--bind)
		BIND_ADDR="$2"
		shift 2
		;;
	--check)
		CHECK_ONLY=1
		shift
		;;
	-h | --help) usage ;;
	*) die "Unknown option: $1" ;;
	esac
done

main "$@"

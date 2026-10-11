#!/bin/bash
# Copy the Caddy-managed certificate for the DoT hostname out to stunnel, and
# reload stunnel only when the content actually changed.
#
# Installed to /usr/local/bin/sync-dot-cert.sh by
# features/setup_dot_resolver.sh (install -m 755 of THIS file) and run daily by
# dot-cert-sync.timer. The installer passes all three arguments, so the
# defaults below only matter for a bare manual run; they match the installer's.
#
# Usage: sync-dot-cert.sh [<domain> [<caddy-container> [<cert-dir>]]]
set -euo pipefail

domain="${1:-dns.kuhy.duckdns.org}"
container="${2:-gitea-caddy}"
cert_dir="${3:-/etc/stunnel/dot}"

# Caddy stores certs per-domain under its data volume.
src="/data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/$domain"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
docker cp "$container:$src/$domain.crt" "$tmp/cert.pem"
docker cp "$container:$src/$domain.key" "$tmp/key.pem"
cat "$tmp/cert.pem" "$tmp/key.pem" >"$tmp/combined.pem"
if ! cmp -s "$tmp/combined.pem" "$cert_dir/combined.pem"; then
	install -m 600 "$tmp/combined.pem" "$cert_dir/combined.pem"
	systemctl reload-or-restart stunnel-dot.service
	echo "certificate updated for $domain"
fi

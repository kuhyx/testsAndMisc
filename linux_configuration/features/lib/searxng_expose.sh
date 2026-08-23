#!/bin/bash
# Caddy snippet, firewall rules and the setup report.
#
# Sourced by setup_searxng.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# --- Phase 5: front it on the public domain ---------------------------------
# Header syntax matters and is easy to get wrong:
#   Header "value"   -> "set"     (REPLACES any existing value)  <-- what we want
#   +Header "value"  -> "add"     (appends, yielding duplicates)
#   >Header "value"  -> "replace" (substring search/replace WITHIN a value —
#                                  NOT a header setter. Using it here silently
#                                  produced no header at all: it adapts to
#                                  {"replace": {"": [{"search_regexp": "..."}]}}
#                                  and matches nothing. Verified via caddy adapt.)
# This matters because SearXNG sends X-Content-Type-Options and Referrer-Policy
# itself via default_http_headers (its Referrer-Policy is `no-referrer`, which
# differs from ours), so the bare/"set" form is required to override rather than
# duplicate them.
write_snippet() {
	cat >"$SEARX_SNIPPET" <<EOF
# Managed by setup_searxng.sh — do not edit by hand.
${SEARX_DOMAIN} {
	header {
		# Bare name = "set" = replace. Do NOT prefix with '+' (appends, causing
		# duplicate headers) or '>' (substring-replace, which sets nothing).
		Content-Security-Policy "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; manifest-src 'self'"
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
		X-Content-Type-Options "nosniff"
		Referrer-Policy "strict-origin-when-cross-origin"
		Permissions-Policy "geolocation=(), microphone=(), camera=(), interest-cohort=()"
		# No HSTS preload: duckdns.org is a public suffix, so kuhy.duckdns.org is
		# the registrable domain — preloading would force HTTPS on every sibling
		# subdomain and is effectively irreversible. Not needed to clear A+.
		-Server
	}
	reverse_proxy 127.0.0.1:${SEARX_PORT} {
		# SearXNG's botdetection needs the real client IP. Without this it logs
		# "X-Forwarded-For nor X-Real-IP header is set!" and 429s every request,
		# including the front page. Paired with trusted_proxies in limiter.toml —
		# both halves are required, neither works alone.
		header_up X-Forwarded-For {http.request.remote.host}
		header_up X-Real-IP {http.request.remote.host}
	}
}
EOF
	log_ok "Wrote ${SEARX_SNIPPET}."
}

# --- Phase 6: reload the edge -----------------------------------------------
reload_caddy() {
	if docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
		docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
		log_ok "Reloaded ${CADDY_CONTAINER}."
	else
		rm -f "$SEARX_SNIPPET"
		die "Caddy config invalid — snippet removed, edge left untouched."
	fi
}

# --- Phase 7: firewall ------------------------------------------------------
# setup_wireguard_ssh.sh owns /etc/nftables.conf and regenerates it from scratch
# — `flush ruleset` and all — on every run, momentarily dropping the whole
# ruleset. Since all this needs is 80/443 already being accepted, check first
# and only pay for the regeneration when the rule is genuinely missing.
web_ports_open() {
	local line ports
	while read -r line; do
		# Exact token membership: a loose regex would also match "8080, 4433".
		ports=",${line//[^0-9,]/},"
		if [[ $ports == *,80,* && $ports == *,443,* ]]; then
			return 0
		fi
	done < <(sudo -n nft list ruleset 2>/dev/null | grep -oE 'tcp dport \{[^}]*\}')
	return 1
}

ensure_firewall() {
	if web_ports_open; then
		log_ok "Ports 80/443 already accepted — leaving the ruleset untouched."
		return 0
	fi
	log_info "Opening ports 80/443 via setup_wireguard_ssh.sh…"
	sudo bash "$WG_SCRIPT" allow-web
}

# --- Phase 8: report --------------------------------------------------------
print_report() {
	cat <<EOF

============================================================================
SearXNG deployed.
============================================================================
  Search : https://${SEARX_DOMAIN}/
  JSON   : https://${SEARX_DOMAIN}/search?q=test&format=json

Next, in order:
  1. Header check (each must print exactly 1):
       for h in content-security-policy strict-transport-security \\
                x-content-type-options referrer-policy permissions-policy; do
         printf '%s: ' "\$h"
         curl -sI https://${SEARX_DOMAIN}/ | grep -ci "^\$h:"
       done
  2. Mozilla Observatory scan of ${SEARX_DOMAIN} — that scan IS the A+ grade.
  3. JSON API FROM ANOTHER MACHINE (phone on cellular, not this host):
       curl 'https://${SEARX_DOMAIN}/search?q=test&format=json'
     A from-host curl cannot surface bot-detection rejection. If this returns
     403/429, fix the limiter allowlist — do NOT disable the limiter.

Acceptance test (do this on your phone):
  Turn Wi-Fi OFF (use cellular) and run a real search at https://${SEARX_DOMAIN}/
============================================================================
EOF
}

setup_cmd() {
	print_setup_header "SearXNG setup"
	preflight
	write_stack
	# The snippet goes into the SHARED sites/ directory, so it is written only
	# after the backend is up and verified. Writing it first means a failure in
	# start_stack leaves an orphan behind that the next `caddy reload` from any
	# other service picks up — the edge then serves this domain as a 502 and
	# starts ACME retries for a host with no backend.
	start_stack
	write_snippet
	reload_caddy
	ensure_firewall
	print_report
	log_ok "SearXNG setup complete."
}

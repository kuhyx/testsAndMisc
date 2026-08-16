#!/bin/bash
# The SearXNG limiter.toml, without which botdetection 429s everything.
#
# Sourced by setup_searxng.sh; split out to keep searxng_stack.sh under
# the 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

write_searx_limiter() {
	# Without this file SearXNG logs "missing config file:
	# /etc/searxng/limiter.toml" and runs with no trusted_proxies, so the
	# forwarded client IP is never trusted and botdetection 429s *everything*.
	cat >"$SEARX_LIMITER" <<'EOF'
# Managed by setup_searxng.sh — do not edit by hand.
[botdetection]

ipv4_prefix = 32
ipv6_prefix = 48

# The edge (gitea-caddy) shares the host network namespace, so its requests
# arrive from loopback. Without 127.0.0.0/8 here the X-Forwarded-For that Caddy
# sends is ignored, every request looks like it came from the proxy itself, and
# rate limiting collapses onto a single bucket.
trusted_proxies = [
  '127.0.0.0/8',
  '::1',
]

[botdetection.ip_limit]
filter_link_local = false
# Off (the shipped default). link_token sends a probe the client must fetch to
# prove it renders HTML, which no scripted JSON client can satisfy. IP-based
# rate limiting below is unaffected and still applies.
link_token = false

[botdetection.ip_lists]
block_ip = []

# pass_ip bypasses ALL botdetection (including the Sec-Fetch/User-Agent probe
# headers) for these addresses.
#
# This is what makes search.formats = [html, json] usable. A scripted JSON
# client — an MCP server, a script — cannot send Sec-Fetch-Mode/Site/Dest, and
# botdetection 429s anything that lacks them, so WITHOUT this entry the JSON API
# is unreachable for every non-browser client. Verified: with browser headers a
# search returns 200 + results; the identical request without Sec-Fetch-* gets
# 429.
#
# Deliberately LOOPBACK ONLY. Requests arriving through the public edge carry
# the real client IP in X-Forwarded-For (trusted_proxies above), so they are
# still fully rate-limited — this exempts only tools running on this host.
pass_ip = [
  '127.0.0.0/8',
  '::1',
]
EOF
	chmod 640 "$SEARX_LIMITER"
	log_ok "Wrote ${SEARX_LIMITER}."
}

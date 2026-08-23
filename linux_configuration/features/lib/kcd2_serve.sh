#!/bin/bash
# Compose stack, Caddy snippet and readiness polling for the dice solver.
#
# Sourced by setup_kcd2_dice_solver.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

# --- Phase 3: the static-serve stack ----------------------------------------
write_serve_stack() {
	ensure_dir "$DICE_DATA_DIR"
	cat >"$DICE_COMPOSE" <<EOF
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
services:
  ${DICE_CONTAINER}:
    image: caddy:2.8
    container_name: ${DICE_CONTAINER}
    restart: unless-stopped
    # host networking is REQUIRED, not a style choice: the nftables forward
    # chain is policy drop with no accept rules, so a bridge-networked
    # container has no outbound egress at all.
    network_mode: host
    volumes:
      - ${DICE_SRC}/dist:/srv:ro
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
EOF

	cat >"$DICE_INNER_CADDY" <<EOF
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
# Static file server on loopback; fronted by ${CADDY_CONTAINER} on the public
# domain.
#
# admin off is REQUIRED: this container shares the host network namespace with
# ${CADDY_CONTAINER}, so without it both would listen on the admin API (:2019)
# and a 'caddy reload' aimed at the edge could be applied here instead — which
# would make this process grab 80/443 and run its own ACME.
#
# auto_https off and the explicit http:// scheme are EQUALLY required, and this
# was found the hard way. A site address of "127.0.0.1:${DICE_PORT}" reads as a
# HOSTNAME, so Caddy turns on automatic HTTPS for it: it issues a local
# certificate, serves TLS on ${DICE_PORT} (so the plain-HTTP health check fails)
# and — the real damage — starts an HTTP->HTTPS redirect listener on :80. Under
# host networking that binds *:80 next to the edge, and SO_REUSEPORT then splits
# inbound HTTP between the two, which would intermittently break ACME
# challenges for every domain on this host.
#
# The site address is port-only and the loopback restriction is done with
# "bind". These are two different things and using the wrong one breaks in a way
# that looks like it works:
#
#   A site address of "http://127.0.0.1:${DICE_PORT}" sets a host MATCHER of
#   127.0.0.1. ${CADDY_CONTAINER} forwards the original "Host:
#   ${DICE_DOMAIN}" header, which then matches no route, and Caddy answers 200
#   with an empty body. A local health check passes (curl sends Host:
#   127.0.0.1) while every real request serves a blank page.
#
#   ":${DICE_PORT}" matches any Host, and "bind 127.0.0.1" restricts the
#   listener itself — which the address never did. Without bind, host
#   networking would expose this unfronted server to the whole LAN.
{
	admin off
	auto_https off
}

:${DICE_PORT} {
	bind 127.0.0.1
	root * /srv
	# Single-page bundle: unknown paths should serve the app, not 404.
	try_files {path} /index.html
	file_server
	encode gzip
}
EOF
	log_ok "Wrote ${DICE_COMPOSE} and ${DICE_INNER_CADDY}."
}

# --- Phase 4: front it on the public domain ---------------------------------
write_snippet() {
	cat >"$DICE_SNIPPET" <<EOF
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
${DICE_DOMAIN} {
	reverse_proxy 127.0.0.1:${DICE_PORT}
}
EOF
	log_ok "Wrote ${DICE_SNIPPET}."
}

# --- Phase 5: start ---------------------------------------------------------
# Sends the Host header the edge will actually forward, and requires a
# non-empty body. A bare "curl http://127.0.0.1:PORT/" sends Host: 127.0.0.1
# and returns an empty 200 against a host-matcher misconfiguration — it passes
# while every real request serves a blank page. Ask the question the edge asks.
wait_for_site() {
	local _ size
	for _ in $(seq 1 30); do
		size="$(curl -s -o /dev/null -w '%{size_download}' \
			-H "Host: ${DICE_DOMAIN}" "http://127.0.0.1:${DICE_PORT}/" 2>/dev/null || echo 0)"
		if [[ ${size:-0} -gt 0 ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

#!/bin/bash
# Edge-conflict checks, site startup and Caddy reload.
#
# Sourced by setup_kcd2_dice_solver.sh; split out to keep kcd2_serve.sh
# under the 250-line cap. Sourced rather than run, so it inherits the
# caller's strict mode and the variables above the source line.

# This container shares the host network namespace with the public edge, so a
# misconfiguration here does not fail locally — it quietly steals a share of
# :80 or :443 from every other site on the box. Gate on it rather than trust
# the config to stay correct.
assert_no_edge_conflict() {
	local pid listeners
	pid="$(docker inspect -f '{{.State.Pid}}' "$DICE_CONTAINER" 2>/dev/null || echo "")"
	[[ -n $pid && $pid != "0" ]] || die "Could not read the ${DICE_CONTAINER} PID."

	listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"

	# Demand positive evidence FIRST. Asserting only the absence of :80/:443
	# fails open: if `ss` returns nothing — a stale PID after a restart, or
	# sudo -n unavailable — every "is it bad?" test misses and the guard happily
	# reports success without having looked at anything.
	if ! grep -qE '(^|[[:space:]])127\.0\.0\.1:'"${DICE_PORT}"'([[:space:]]|$)' <<<"$listeners"; then
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "Could not confirm ${DICE_CONTAINER} listens on 127.0.0.1:${DICE_PORT}. Container stopped."
	fi
	if grep -qE ':(80|443)\b' <<<"$listeners"; then
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "${DICE_CONTAINER} bound :80/:443 — it would contend with ${CADDY_CONTAINER}. Container stopped."
	fi
	# Must be on loopback, not 0.0.0.0/*: host networking would otherwise expose
	# the unfronted static server to the whole LAN.
	if grep -qE '(\*|0\.0\.0\.0):'"${DICE_PORT}"'\b' <<<"$listeners"; then
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "${DICE_CONTAINER} bound ${DICE_PORT} on all interfaces, not loopback. Container stopped."
	fi
	log_ok "${DICE_CONTAINER} listens on loopback:${DICE_PORT} only — no contention, not LAN-exposed."
}

start_site() {
	log_info "Starting the ${DICE_CONTAINER} container…"
	docker compose -f "$DICE_COMPOSE" up -d
	if wait_for_site; then
		log_ok "Solver answering on http://127.0.0.1:${DICE_PORT}/."
	else
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "Solver did not become reachable on 127.0.0.1:${DICE_PORT} (container stopped)."
	fi
	assert_no_edge_conflict
}

# --- Phase 6: reload the edge -----------------------------------------------
reload_caddy() {
	if docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
		docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
		log_ok "Reloaded ${CADDY_CONTAINER}."
	else
		die "Caddy config invalid — aborting reload. Check ${SITES_DIR}/*.caddy."
	fi
}

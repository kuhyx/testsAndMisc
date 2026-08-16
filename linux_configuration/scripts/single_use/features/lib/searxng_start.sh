#!/bin/bash
# Readiness polling, loopback assertion and stack startup.
#
# Sourced by setup_searxng.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# --- Phase 3/4: start -------------------------------------------------------
# Sends the Host header the edge will actually forward, and requires a
# non-empty body. A bare "curl http://127.0.0.1:PORT/" against a host-matcher
# misconfiguration returns an empty 200 — it passes while every real request
# serves a blank page.
wait_for_site() {
	local _ size
	for _ in $(seq 1 60); do
		# Browser-shaped headers: without them botdetection answers 429 and this
		# readiness probe would spin for its full 60s against a healthy backend.
		size="$(curl -s --compressed -o /dev/null -w '%{size_download}' \
			-A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' \
			-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
			-H 'Accept-Language: en-US,en;q=0.9' \
			-H 'Accept-Encoding: gzip, deflate, br' \
			-H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-Dest: document' \
			-H "Host: ${SEARX_DOMAIN}" "http://127.0.0.1:${SEARX_PORT}/" 2>/dev/null || echo 0)"
		if [[ ${size:-0} -gt 0 ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

wait_for_valkey() {
	local _ out
	for _ in $(seq 1 30); do
		out="$(docker exec "$VALKEY_CONTAINER" valkey-cli -h 127.0.0.1 -p "$VALKEY_PORT" ping 2>/dev/null || true)"
		if [[ $out == "PONG" ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

# These containers share the host network namespace with the public edge, so a
# misconfiguration does not fail locally — it quietly exposes an unfronted
# service to the whole LAN, or steals a share of :80/:443 from every other site
# on the box. Gate on it rather than trust the config to stay correct.
assert_loopback_only() {
	local container="$1" port="$2" pid listeners
	pid="$(docker inspect -f '{{.State.Pid}}' "$container" 2>/dev/null || echo "")"
	[[ -n $pid && $pid != "0" ]] || die "Could not read the ${container} PID."

	listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"

	# Demand positive evidence FIRST. Asserting only the absence of a bad bind
	# fails open: if `ss` returns nothing — a stale PID, or sudo -n unavailable —
	# every "is it bad?" test misses and the guard reports success having looked
	# at nothing.
	if ! grep -qE '(^|[[:space:]])127\.0\.0\.1:'"${port}"'([[:space:]]|$)' <<<"$listeners"; then
		docker stop "$container" >/dev/null 2>&1 || true
		die "Could not confirm ${container} listens on 127.0.0.1:${port}. Container stopped."
	fi
	if grep -qE ':(80|443)\b' <<<"$listeners"; then
		docker stop "$container" >/dev/null 2>&1 || true
		die "${container} bound :80/:443 — it would contend with ${CADDY_CONTAINER}. Container stopped."
	fi
	# Reject *, 0.0.0.0 AND [::] — granian's real default is ::, which a
	# 0.0.0.0-only check would sail straight past.
	if grep -qE '(\*|0\.0\.0\.0|\[::\]):'"${port}"'\b' <<<"$listeners"; then
		docker stop "$container" >/dev/null 2>&1 || true
		die "${container} bound ${port} on all interfaces, not loopback. Container stopped."
	fi
	log_ok "${container} listens on loopback:${port} only — no contention, not LAN-exposed."
}

start_stack() {
	log_info "Starting valkey + searxng…"
	docker compose -f "$SEARX_COMPOSE" up -d
	# `up -d` is a no-op when only a BIND-MOUNTED config file changed — compose
	# compares the compose spec, not the files it mounts. settings.yml and
	# limiter.toml are read once at startup, so without an explicit restart the
	# container keeps serving the previous config and every verification below
	# silently tests the OLD deployment. (Hit for real: limiter.toml was written
	# at 15:06 while the container had been running since 15:02, so botdetection
	# kept 429ing with "missing config file".)
	log_info "Restarting searxng to pick up settings.yml / limiter.toml…"
	docker restart "$SEARX_CONTAINER" >/dev/null

	if wait_for_valkey; then
		log_ok "valkey answering PING on 127.0.0.1:${VALKEY_PORT}."
	else
		die "valkey did not become ready — the limiter would silently no-op."
	fi

	if wait_for_site; then
		log_ok "SearXNG answering on http://127.0.0.1:${SEARX_PORT}/."
	else
		docker stop "$SEARX_CONTAINER" >/dev/null 2>&1 || true
		die "SearXNG did not become reachable on 127.0.0.1:${SEARX_PORT} (container stopped)."
	fi

	assert_loopback_only "$VALKEY_CONTAINER" "$VALKEY_PORT"
	assert_loopback_only "$SEARX_CONTAINER" "$SEARX_PORT"
}

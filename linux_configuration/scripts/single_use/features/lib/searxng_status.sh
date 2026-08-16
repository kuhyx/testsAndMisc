#!/bin/bash
# The status subcommand and its HTTP, container and header checks.
#
# Sourced by setup_searxng.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# --- status: self-diagnose --------------------------------------------------
status_line() {
	if [[ $1 -eq 0 ]]; then
		log_ok "$2"
	else
		log_warn "$2"
	fi
}

check_http() {
	# Prints 0 to stdout if the URL returns 200 with a non-empty body, else 1.
	# The body-size check matters: a host-matcher misconfiguration answers 200
	# with nothing in it, which a status-only check would call healthy.
	# Certificates are NOT skipped — `curl -k` would report a failed-ACME cert as
	# healthy, which is exactly the green-while-broken this exists to catch.
	# Browser-shaped headers are REQUIRED, not cosmetic. botdetection runs a
	# separate check per header and 429s on the FIRST one that fails, so the full
	# set below must be sent every time. All four matter:
	#   Accept-Language   -> http_accept_language   (omitting this alone 429s)
	#   Accept-Encoding   -> http_accept_encoding   (needs gzip or deflate)
	#   Accept            -> http_accept
	#   Sec-Fetch-*       -> http_sec_fetch         (302-redirects when invalid)
	# Diagnosing which one bit is easy but non-obvious: set `debug: true` under
	# general: in settings.yml, restart, and the log prints
	# "NOT OK (searx.botdetection.<method>)" naming the exact check.
	# (Observed: dropping only Accept-Language turned a healthy 200 into a 429.)
	local url="$1" out code size
	out="$(curl -s --compressed -o /dev/null -w '%{http_code} %{size_download}' --max-time 10 \
		-A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' \
		-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
		-H 'Accept-Language: en-US,en;q=0.9' \
		-H 'Accept-Encoding: gzip, deflate, br' \
		-H 'Sec-Fetch-Mode: navigate' \
		-H 'Sec-Fetch-Site: none' \
		-H 'Sec-Fetch-Dest: document' \
		${2:+-H "Host: $2"} "$url" 2>/dev/null || echo "000 0")"
	read -r code size <<<"$out"
	[[ $code == "200" && ${size:-0} -gt 0 ]] && echo 0 || echo 1
}

check_container() {
	local name="$1" port="$2" pid listeners
	if ! docker ps --format '{{.Names}}' | grep -qx "$name"; then
		status_line 1 "${name} container not running"
		return
	fi
	status_line 0 "${name} container running"
	pid="$(docker inspect -f '{{.State.Pid}}' "$name" 2>/dev/null || echo "")"
	listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"
	if [[ -z $listeners ]]; then
		status_line 1 "${name}: could not read listeners (needs sudo -n) — binding UNVERIFIED"
	elif grep -qE '(\*|0\.0\.0\.0|\[::\]):'"${port}"'\b' <<<"$listeners"; then
		status_line 1 "${name} is bound to ALL INTERFACES on ${port} — LAN-exposed"
	elif grep -qE '(^|[[:space:]])127\.0\.0\.1:'"${port}"'([[:space:]]|$)' <<<"$listeners"; then
		status_line 0 "${name} listens on loopback:${port} only"
	else
		status_line 1 "${name} not listening on ${port} as expected"
	fi
}

# Duplicated headers are the classic silent A+ killer, so count them rather than
# merely checking presence.
check_headers() {
	local headers out h count
	# Same browser-header requirement as check_http — a 429 carries none of these
	# headers, so a bare curl would report all five as MISSING on a healthy site.
	out="$(curl -sI --compressed --max-time 10 \
		-A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' \
		-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
		-H 'Accept-Language: en-US,en;q=0.9' \
		-H 'Accept-Encoding: gzip, deflate, br' \
		-H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-Dest: document' \
		"https://${SEARX_DOMAIN}/" 2>/dev/null || true)"
	if [[ -z $out ]]; then
		status_line 1 "could not fetch headers from https://${SEARX_DOMAIN}/"
		return
	fi
	headers=(content-security-policy strict-transport-security
		x-content-type-options referrer-policy permissions-policy)
	for h in "${headers[@]}"; do
		count="$(grep -ci "^${h}:" <<<"$out" || true)"
		if [[ $count -eq 1 ]]; then
			status_line 0 "header ${h}: exactly 1"
		elif [[ $count -eq 0 ]]; then
			status_line 1 "header ${h}: MISSING"
		else
			status_line 1 "header ${h}: DUPLICATED (${count}) — costs the A+ grade"
		fi
	done
}

status_cmd() {
	print_setup_header "SearXNG status"

	if has_cmd docker; then
		status_line 0 "docker present"
	else
		status_line 1 "docker missing"
	fi

	# NOTE: deliberately no ownership/mode assertion on settings.yml — the
	# entrypoint chowns the bind mount to uid 977, so a "must be kuhy-owned,
	# mode 600" check would false-fail on every run after first start.
	if [[ -f $SEARX_SETTINGS ]]; then
		status_line 0 "settings.yml present"
	else
		status_line 1 "settings.yml missing — run setup"
	fi
	# Its absence is not cosmetic: with no limiter.toml there are no
	# trusted_proxies, so botdetection 429s every request including the homepage.
	if [[ -f $SEARX_LIMITER ]]; then
		status_line 0 "limiter.toml present"
	else
		status_line 1 "limiter.toml missing — botdetection will 429 everything"
	fi

	check_container "$VALKEY_CONTAINER" "$VALKEY_PORT"
	check_container "$SEARX_CONTAINER" "$SEARX_PORT"

	# The limiter silently no-ops when valkey is unreachable, so a working search
	# does NOT prove the limiter works. Check the backend directly.
	local ping
	ping="$(docker exec "$VALKEY_CONTAINER" valkey-cli -h 127.0.0.1 -p "$VALKEY_PORT" ping 2>/dev/null || true)"
	if [[ $ping == "PONG" ]]; then
		status_line 0 "valkey reachable — limiter backend live"
	else
		status_line 1 "valkey NOT reachable — the limiter is silently disabled"
	fi

	status_line "$(check_http "http://127.0.0.1:${SEARX_PORT}/" "$SEARX_DOMAIN")" \
		"local SearXNG (127.0.0.1:${SEARX_PORT}, Host: ${SEARX_DOMAIN})"

	if [[ -f $SEARX_SNIPPET ]]; then
		status_line 0 "Caddy snippet present"
	else
		status_line 1 "Caddy snippet missing"
	fi
	if getent hosts "$SEARX_DOMAIN" >/dev/null; then
		status_line 0 "${SEARX_DOMAIN} resolves"
	else
		status_line 1 "${SEARX_DOMAIN} does not resolve"
	fi
	status_line "$(check_http "https://${SEARX_DOMAIN}/")" \
		"external https://${SEARX_DOMAIN}/"

	check_headers

	# A loading front page proves nothing about the actual product. Egress is the
	# fragile part on this host (bridge networking has no outbound access at all),
	# so run a real query and require real results. Uses the loopback JSON API,
	# which pass_ip exempts from botdetection.
	local json hits
	json="$(curl -s --compressed --max-time 30 \
		"http://127.0.0.1:${SEARX_PORT}/search?q=arch+linux&format=json" 2>/dev/null || true)"
	hits="$(grep -o '"url"' <<<"$json" | wc -l)"
	if [[ ${hits:-0} -gt 0 ]]; then
		status_line 0 "live search returned ${hits} results (engines reachable)"
	else
		status_line 1 "live search returned NO results — check egress/engines"
	fi
	# Surfaces engines that are failing rather than merely slow; these are the
	# candidates for pruning.
	local dead
	dead="$(grep -oE '"unresponsive_engines": \[\[[^]]*' <<<"$json" | head -c 300 || true)"
	[[ -n $dead ]] && log_info "unresponsive engines: ${dead#*: }"

	# After pruning, general search is served by google cse alone (google/bing
	# are inactive: true upstream and only answer to !go / !bi). That is a single
	# point of failure worth naming explicitly rather than discovering as "no
	# results", so check the engine that is actually carrying the category.
	if [[ ${hits:-0} -eq 0 ]]; then
		log_warn "general search has no working engine — try: !go <query> / !bi <query>,"
		log_warn "or re-enable an engine in the 'engines:' block of ${SEARX_SETTINGS}"
	fi

	log_info "Not checked here (needs another machine): the JSON API under bot"
	log_info "detection. Run from your phone on cellular, not from this host:"
	log_info "  curl 'https://${SEARX_DOMAIN}/search?q=test&format=json'"
}

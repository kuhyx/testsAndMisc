#!/bin/bash
# CV build, website generation and the Caddy stack snippets.
#
# Sourced by setup_personal_website.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

# --- Phase 5: build the website --------------------------------------------
build_website() {
	log_info "Installing website dependencies and building…"
	(
		cd "$WEBSITE_SRC" || die "Cannot enter ${WEBSITE_SRC}."
		pnpm install --frozen-lockfile
		pnpm run build
	)
	[[ -f "${WEBSITE_SRC}/dist/index.html" ]] ||
		die "Build did not produce ${WEBSITE_SRC}/dist/index.html."
	log_ok "Website built to ${WEBSITE_SRC}/dist."
}

# --- Phase 6: write the website's static-serve stack ------------------------
write_website_stack() {
	ensure_dir "$WEBSITE_DATA_DIR"
	cat >"$WEBSITE_COMPOSE" <<EOF
# Managed by setup_personal_website.sh — do not edit by hand.
services:
  personal-website:
    image: caddy:2.8
    container_name: personal-website
    restart: unless-stopped
    network_mode: host
    volumes:
      - ${WEBSITE_SRC}/dist:/srv:ro
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
EOF

	cat >"$WEBSITE_INNER_CADDY" <<EOF
# Managed by setup_personal_website.sh — do not edit by hand.
# Static file server on loopback; fronted by gitea-caddy on the public domain.
#
# admin off is REQUIRED: this container shares the host network namespace with
# gitea-caddy, so without it both Caddies would listen on the admin API (:2019)
# and a 'caddy reload' aimed at gitea-caddy could be applied to this one instead
# — which would make it grab 80/443 and run ACME. Disabling admin keeps this
# process strictly a loopback static server on ${WEBSITE_PORT}.
{
	admin off
}

:${WEBSITE_PORT} {
	root * /srv
	# {path}/index.html is the load-bearing middle term: the website
	# prerenders each blog post to dist/blog/<slug>/index.html, and
	# try_files does NOT resolve a directory to its index on its own.
	# Without it every post silently falls through to the SPA shell and
	# is served as the landing page -- right content once React boots,
	# wrong <title> and no link preview, which looks like nothing is
	# wrong until you check the tab.
	try_files {path} {path}/index.html /index.html
	file_server
	encode gzip
}
EOF
	log_ok "Wrote ${WEBSITE_COMPOSE} and ${WEBSITE_INNER_CADDY}."
}

# --- Phase 7: front the website on the root domain --------------------------
write_website_snippet() {
	cat >"$WEBSITE_SNIPPET" <<EOF
# Managed by setup_personal_website.sh — do not edit by hand.
${WEBSITE_DOMAIN} {
	reverse_proxy 127.0.0.1:${WEBSITE_PORT}
}
EOF
	log_ok "Wrote ${WEBSITE_SNIPPET}."
}

# --- Phase 8: start the website container -----------------------------------
# Last HTTP status seen by wait_for_website, so a failure can say whether the
# server was unreachable or merely answering wrongly. Those are different bugs
# and the old message named only the first one.
WEBSITE_LAST_CODE=""

wait_for_website() {
	local _
	for _ in $(seq 1 30); do
		WEBSITE_LAST_CODE="$(curl -s -o /dev/null -w '%{http_code}' \
			--max-time 5 "http://127.0.0.1:${WEBSITE_PORT}/" || echo "000")"
		if [[ "$WEBSITE_LAST_CODE" == "200" ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

start_website() {
	log_info "Starting the personal-website container…"
	# --force-recreate is required, not tidiness. Two failure modes need it,
	# and compose cannot see either one:
	#
	#   1. The Caddyfile is a BIND MOUNT, so its contents are not part of the
	#      container's config hash. Editing it changes nothing compose compares,
	#      it reports "Running", and the new directives never load. A blog post
	#      served as the landing page is exactly this bug.
	#   2. A bind mount is resolved once, at container start. Anything that
	#      replaces dist/ rather than emptying it (rm -rf, a git clean, moving
	#      the checkout) leaves the container mounted on the old, unlinked
	#      inode -- /srv reads as empty and every request 404s while the
	#      container still looks healthy.
	#
	# Recreating is under a second for a static file server, so it is cheaper
	# than either failure being diagnosed by hand.
	docker compose -f "$WEBSITE_COMPOSE" up -d --force-recreate
	if wait_for_website; then
		log_ok "Website answering on http://127.0.0.1:${WEBSITE_PORT}/."
	else
		if [[ "$WEBSITE_LAST_CODE" == "000" ]]; then
			die "Website unreachable on 127.0.0.1:${WEBSITE_PORT} (no response)."
		fi
		die "Website on 127.0.0.1:${WEBSITE_PORT} answered HTTP ${WEBSITE_LAST_CODE}, not 200. \
A 404 here usually means the container's /srv bind mount is stale or ${WEBSITE_SRC}/dist is empty."
	fi
}

# --- Phase 9: reload the edge -----------------------------------------------
reload_caddy() {
	if docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
		docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
		log_ok "Reloaded ${CADDY_CONTAINER}."
	else
		die "Caddy config invalid — aborting reload. Check ${SITES_DIR}/*.caddy."
	fi
}

# --- Phase 10: firewall -----------------------------------------------------
ensure_firewall() {
	log_info "Ensuring ports 80/443 are open (idempotent)…"
	sudo bash "$WG_SCRIPT" allow-web
}

# --- Phase 11: report -------------------------------------------------------
print_report() {
	cat <<EOF

============================================================================
Personal website deployed.
============================================================================
  Website : https://${WEBSITE_DOMAIN}/
  Gitea   : https://${GITEA_DOMAIN}/   (moved from the root)

Gitea moved to a subdomain. Re-point any local clones/mirrors:
  git remote set-url <name> https://${GITEA_DOMAIN}/<owner>/<repo>.git

Acceptance test (do this on your phone):
  Turn Wi-Fi OFF (use cellular) and open https://${WEBSITE_DOMAIN}/ —
  it should load over HTTPS with the hero, live GitHub projects, and CV,
  and be usable at phone width.
============================================================================
EOF
}

setup_cmd() {
	print_setup_header "Personal website setup"
	preflight
	migrate_caddy_snippets
	relocate_gitea
	build_cv_json
	build_website
	write_website_stack
	write_website_snippet
	start_website
	reload_caddy
	ensure_firewall
	print_report
	deploy_admin_service
	log_ok "Personal website setup complete."
}

# --- status: self-diagnose --------------------------------------------------
status_line() {
	if [[ $1 -eq 0 ]]; then
		log_ok "$2"
	else
		log_warn "$2"
	fi
}

check_http() {
	# Prints 0 to stdout if the URL returns 200, else 1.
	local url="$1" code
	code="$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || echo 000)"
	[[ $code == "200" ]] && echo 0 || echo 1
}

status_cmd() {
	print_setup_header "Personal website status"
	admin_status_lines

	if has_cmd node; then
		status_line 0 "node present"
	else
		status_line 1 "node missing"
	fi
	if has_cmd pnpm; then
		status_line 0 "pnpm present"
	else
		status_line 1 "pnpm missing"
	fi
	if [[ -f "${WEBSITE_SRC}/dist/index.html" ]]; then
		status_line 0 "build present (dist/index.html)"
	else
		status_line 1 "build missing — run setup"
	fi
	if docker ps --format '{{.Names}}' | grep -qx personal-website; then
		status_line 0 "personal-website container running"
	else
		status_line 1 "personal-website container not running"
	fi

	status_line "$(check_http "http://127.0.0.1:${WEBSITE_PORT}/")" \
		"local static server (127.0.0.1:${WEBSITE_PORT})"

	if [[ -f $WEBSITE_SNIPPET ]]; then
		status_line 0 "Caddy website snippet present"
	else
		status_line 1 "Caddy website snippet missing"
	fi
	if grep -qE '^[[:space:]]*import[[:space:]]+/etc/caddy/sites' "$CADDYFILE" 2>/dev/null; then
		status_line 0 "root Caddyfile uses snippet imports"
	else
		status_line 1 "root Caddyfile not migrated to imports"
	fi
	if getent hosts "$WEBSITE_DOMAIN" >/dev/null; then
		status_line 0 "${WEBSITE_DOMAIN} resolves"
	else
		status_line 1 "${WEBSITE_DOMAIN} does not resolve"
	fi
	if getent hosts "$GITEA_DOMAIN" >/dev/null; then
		status_line 0 "${GITEA_DOMAIN} resolves"
	else
		status_line 1 "${GITEA_DOMAIN} does not resolve"
	fi
	status_line "$(check_http "https://${WEBSITE_DOMAIN}/")" \
		"external https://${WEBSITE_DOMAIN}/"
	status_line "$(check_http "https://${GITEA_DOMAIN}/")" \
		"external https://${GITEA_DOMAIN}/"
}

#!/bin/bash
# Caddy vhost, DuckDNS record and firewall rules for exposing SyncYomi.
#
# Sourced by setup_syncyomi.sh; split out to keep syncyomi_stack.sh under
# the 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

# --- Step 6: Caddy reverse-proxy block (append + reload) ---------------------
configure_caddy() {
	local snippet="${CADDY_SITES_DIR}/${SYNCYOMI_SUBDOMAIN}.caddy"
	local desired
	desired="$(printf '# Managed by setup_syncyomi.sh.\n%s {\n\treverse_proxy 127.0.0.1:%s\n}' \
		"${SYNCYOMI_SUBDOMAIN}" "${SYNCYOMI_PORT}")"

	grep -qE '^[[:space:]]*import[[:space:]]+/etc/caddy/sites' "${CADDYFILE}" ||
		die "Root Caddyfile does not import sites/ — run setup_personal_website.sh first."

	# Every service on this edge owns one snippet under sites/. Writing into the
	# shared Caddyfile instead is what produced "ambiguous site definition" on
	# 2026-08-28: the site was already defined in its snippet, the block was
	# appended a second time, and the reload failed while the edge kept serving
	# the last config it had accepted — so the damage only showed up later.
	ensure_dir "${CADDY_SITES_DIR}"
	if [[ -f ${snippet} && "$(cat "${snippet}")" == "${desired}" ]]; then
		log_ok "Caddy snippet already current: ${snippet}"
	else
		log_info "Writing Caddy snippet ${snippet}"
		printf '%s\n' "${desired}" >"${snippet}"
	fi

	if grep -qE "^${SYNCYOMI_SUBDOMAIN} \{" "${CADDYFILE}"; then
		log_info "Removing the legacy inline ${SYNCYOMI_SUBDOMAIN} block from ${CADDYFILE}"
		sed -i -E "/^${SYNCYOMI_SUBDOMAIN} \{/,/^\}/d" "${CADDYFILE}"
	fi

	docker exec "${CADDY_CONTAINER}" caddy validate --config "${CADDYFILE_IN_CONTAINER}" >/dev/null 2>&1 ||
		die "Caddy config invalid — not reloading. Check ${CADDY_SITES_DIR}/*.caddy."
	docker exec "${CADDY_CONTAINER}" caddy reload --config "${CADDYFILE_IN_CONTAINER}" ||
		die "caddy reload failed — check 'docker logs ${CADDY_CONTAINER}'."
	log_ok "Caddy reloaded (auto-HTTPS will be issued once the subdomain resolves)"
}

# --- Step 7: DuckDNS subdomain (extend existing updater; no new cron) --------
configure_duckdns() {
	local label="${SYNCYOMI_SUBDOMAIN%.duckdns.org}"
	if grep -qE "domains=[^&\"']*${label}([,&\"']|$)" "${DUCKDNS_UPDATER}"; then
		log_ok "DuckDNS updater already includes '${label}'"
	else
		log_info "Adding '${label}' to the existing DuckDNS updater"
		sed -i -E "s|(domains=)([^&\"']*)|\1\2,${label}|" "${DUCKDNS_UPDATER}"
	fi
	# Refresh now (harmless if the subdomain isn't registered yet).
	bash "${DUCKDNS_UPDATER}" >/dev/null 2>&1 || log_warn "DuckDNS update returned non-zero (register the subdomain first)."
	if getent hosts "${SYNCYOMI_SUBDOMAIN}" >/dev/null 2>&1; then
		log_ok "${SYNCYOMI_SUBDOMAIN} resolves"
	else
		log_warn "${SYNCYOMI_SUBDOMAIN} does not resolve yet — create the '${label}' subdomain in the DuckDNS dashboard."
	fi
}

# --- Step 8: firewall (open 80/443 via the owning script, idempotent) -------
ensure_firewall() {
	if sudo nft list ruleset 2>/dev/null | grep -qE 'dport \{[^}]*80[^}]*443'; then
		log_ok "Firewall already allows tcp/80 + tcp/443"
	elif [[ -f ${WG_SCRIPT} ]]; then
		log_info "Opening 80/443 via setup_wireguard_ssh.sh allow-web"
		sudo bash "${WG_SCRIPT}" allow-web
	else
		log_warn "setup_wireguard_ssh.sh not found — ensure tcp/80+443 are open."
	fi
}

# --- Step 9: report ----------------------------------------------------------
print_report() {
	local url="https://${SYNCYOMI_SUBDOMAIN}"
	local key="(create one in the web UI)"
	[[ -f ${TOKEN_FILE} ]] && key="$(<"${TOKEN_FILE}")"
	cat <<EOF

============================================================================
  SyncYomi is up.
    Host address : ${url}
    API key      : ${key}
    Web UI login : ${SYNCYOMI_USER} / (password in ${CONF_FILE})

  TachiyomiSY setup (on the phone):
    Settings → Data & storage → Sync → SyncYomi
      Host    : ${url}
      API key : ${key}
    Use the SAME API key on every device you want to sync.

  If the subdomain is new, create it once in the DuckDNS dashboard
  (label: ${SYNCYOMI_SUBDOMAIN%.duckdns.org}) so Caddy can issue TLS.

  Acceptance test: on your phone with Wi-Fi OFF (cellular), configure the
  sync above and confirm the library round-trips.
============================================================================
EOF
}

# --- status subcommand -------------------------------------------------------
status_cmd() {
	print_setup_header "SyncYomi status"
	echo
	if [[ -f ${COMPOSE_FILE} ]]; then
		docker compose -f "${COMPOSE_FILE}" ps
	else
		log_warn "No compose file at ${COMPOSE_FILE}"
	fi
	echo

	local code
	code="$(syncyomi_ready "${SYNCYOMI_LOCAL}" || true)"
	if [[ ${code} == "204" || ${code} == "403" ]]; then
		log_ok "Local API answering (${SYNCYOMI_LOCAL}, HTTP ${code})"
	else
		log_warn "Local API not answering (HTTP ${code:-none})"
	fi

	local sub="${SYNCYOMI_SUBDOMAIN:-kuhy-sync.duckdns.org}"
	if [[ -f ${CONF_FILE} ]]; then
		# shellcheck source=/dev/null
		source "${CONF_FILE}"
		sub="${SYNCYOMI_SUBDOMAIN}"
	fi

	if grep -qE "^${sub} \{" "${CADDYFILE}" 2>/dev/null; then
		log_ok "Caddy block present for ${sub}"
	else
		log_warn "No Caddy block for ${sub}"
	fi

	if getent hosts "${sub}" >/dev/null 2>&1; then
		log_ok "${sub} resolves"
	else
		log_warn "${sub} does not resolve"
	fi

	code="$(syncyomi_ready "https://${sub}" || true)"
	if [[ ${code} == "204" || ${code} == "403" ]]; then
		log_ok "External HTTPS reachable (https://${sub}, HTTP ${code})"
	else
		log_warn "External HTTPS not reachable yet (HTTP ${code:-none})"
	fi
}

# --- main --------------------------------------------------------------------
setup_cmd() {
	print_setup_header "Self-hosted SyncYomi manga sync"
	preflight
	load_config
	write_compose
	start_containers
	wait_for_syncyomi
	ensure_local_config
	mint_api_key
	configure_caddy
	configure_duckdns
	ensure_firewall
	print_report
}

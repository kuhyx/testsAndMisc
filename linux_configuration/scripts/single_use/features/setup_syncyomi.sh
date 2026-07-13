#!/bin/bash
# setup_syncyomi.sh — Self-hosted SyncYomi manga-sync server on this Arch PC.
#
# Stands up SyncYomi (github.com/SyncYomi/SyncYomi) in Docker, bound to
# 127.0.0.1:8282, and fronts it with the EXISTING Caddy reverse proxy (from
# setup_gitea.sh) for automatic public HTTPS at a new DuckDNS subdomain, so
# TachiyomiSY on the phone can sync its library from a mobile network.
#
# It reuses the host's existing exposure stack — it does NOT add a second Caddy,
# a second DuckDNS updater, or hand-edit /etc/nftables.conf. It also creates the
# first SyncYomi account and mints an API key over the local REST API, then
# prints the host address + API key ready to paste into TachiyomiSY.
#
# Run as your normal user (NOT root). It uses sudo only for pacman, the firewall
# flag and enabling docker. Idempotent — safe to re-run.
#
# Usage:
#   ./setup_syncyomi.sh          Install / update everything (default)
#   ./setup_syncyomi.sh setup    Same as above
#   ./setup_syncyomi.sh status   Show health / exposure diagnostics
#   ./setup_syncyomi.sh help     Show this help

set -euo pipefail

# --- Pinned SyncYomi image ---------------------------------------------------
readonly SYNCYOMI_IMAGE="ghcr.io/syncyomi/syncyomi:v1.1.11"
readonly SYNCYOMI_PORT=8282
readonly SYNCYOMI_LOCAL="http://127.0.0.1:${SYNCYOMI_PORT}"

# --- Data dir + secrets (outside the git repo, like ~/gitea) -----------------
readonly DATA_DIR="${HOME}/syncyomi"
readonly COMPOSE_FILE="${DATA_DIR}/docker-compose.yml"
readonly CONFIG_TOML="${DATA_DIR}/config/config.toml"
readonly CONF_FILE="${DATA_DIR}/.syncyomi.conf"
readonly TOKEN_FILE="${DATA_DIR}/.api_token"

# --- Existing host infrastructure (from setup_gitea.sh / install_joplin.sh) --
readonly CADDY_CONTAINER="gitea-caddy"
readonly CADDYFILE="${HOME}/gitea/Caddyfile"
readonly CADDYFILE_IN_CONTAINER="/etc/caddy/Caddyfile"
readonly DUCKDNS_UPDATER="${HOME}/.joplin-server/duckdns-update.sh"

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"

# shellcheck source=../../lib/common.sh
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../../lib/common.sh"

# Config values (populated from CONF_FILE / defaults).
SYNCYOMI_USER=""
SYNCYOMI_PASSWORD=""
SYNCYOMI_SUBDOMAIN=""

# Local timezone for the container (falls back if timedatectl is unavailable).
TZ_VALUE="$(timedatectl show -p Timezone --value 2>/dev/null || echo 'Europe/Warsaw')"
readonly TZ_VALUE

die() {
	log_error "$1"
	exit 1
}

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit 0
}

# --- Step 1: preflight -------------------------------------------------------
preflight() {
	log_info "Preflight checks"
	[[ ${EUID} -ne 0 ]] || die "Run as your normal user, not root (it will sudo where needed)."

	# Runtime deps; install any that are missing from the official repos.
	install_missing_pacman_packages docker docker-compose jq curl openssl

	# Ensure the docker daemon is enabled+running (auto-start after reboot). Only
	# touch systemd via sudo when it is not already active, to stay a no-op on the
	# common case where docker is already up (Gitea/dufs run on it).
	has_cmd docker || die "docker not found — run setup_gitea.sh first."
	if ! is_service_active docker; then
		log_info "Enabling and starting docker.service"
		sudo systemctl enable --now docker
	fi

	# The public-exposure stack must already exist (Caddy from setup_gitea.sh).
	docker ps --format '{{.Names}}' | grep -qx "${CADDY_CONTAINER}" ||
		die "Caddy container '${CADDY_CONTAINER}' not running — run setup_gitea.sh first."
	[[ -f ${CADDYFILE} ]] || die "Caddyfile ${CADDYFILE} missing — run setup_gitea.sh first."
	[[ -x ${DUCKDNS_UPDATER} ]] || die "DuckDNS updater ${DUCKDNS_UPDATER} missing — run install_joplin.sh first."
	log_ok "Host exposure stack present (docker + ${CADDY_CONTAINER} + DuckDNS updater)"
}

# --- Step 2: config (auto-generate credentials, store 0600) ------------------
load_config() {
	ensure_dir "${DATA_DIR}"
	chmod 700 "${DATA_DIR}"
	if [[ -f ${CONF_FILE} ]]; then
		# shellcheck source=/dev/null
		source "${CONF_FILE}"
	fi
	SYNCYOMI_USER="${SYNCYOMI_USER:-$(get_actual_user)}"
	SYNCYOMI_SUBDOMAIN="${SYNCYOMI_SUBDOMAIN:-kuhy-sync.duckdns.org}"
	# Generate the web/API password once; never regenerate on re-run.
	if [[ -z ${SYNCYOMI_PASSWORD:-} ]]; then
		SYNCYOMI_PASSWORD="$(openssl rand -base64 24)"
	fi
	save_config
}

save_config() {
	# 0600 — holds the plaintext SyncYomi password so re-runs stay
	# non-interactive. Lives under ~/syncyomi (outside the git repo).
	umask 077
	{
		printf 'SYNCYOMI_USER=%q\n' "${SYNCYOMI_USER}"
		printf 'SYNCYOMI_PASSWORD=%q\n' "${SYNCYOMI_PASSWORD}"
		printf 'SYNCYOMI_SUBDOMAIN=%q\n' "${SYNCYOMI_SUBDOMAIN}"
	} >"${CONF_FILE}"
	chmod 600 "${CONF_FILE}"
	log_ok "Saved config to ${CONF_FILE} (0600)"
}

# --- Step 3: docker-compose stack (host networking, loopback bind) -----------
write_compose() {
	ensure_dir "${DATA_DIR}/config"
	# network_mode: host + SyncYomi's host=127.0.0.1 keeps it loopback-only
	# (reached by the host-networked Caddy) and dodges this host's default-drop
	# nftables FORWARD chain that would kill a bridge-networked container.
	umask 077
	cat >"${COMPOSE_FILE}" <<EOF
# Generated by setup_syncyomi.sh — do not edit by hand.
services:
  syncyomi:
    container_name: syncyomi
    image: ${SYNCYOMI_IMAGE}
    restart: unless-stopped
    network_mode: host
    environment:
      - TZ=${TZ_VALUE}
    volumes:
      - ./config:/config
EOF
	log_ok "Wrote ${COMPOSE_FILE}"
}

start_containers() {
	log_info "Starting SyncYomi container"
	docker compose -f "${COMPOSE_FILE}" up -d
}

# Readiness probe. SyncYomi (v1.1.x) has no public /healthz, but GET
# /api/auth/onboard answers 204 (no user yet) or 403 (a user exists) once the
# API is serving — either means "up". Echoes the HTTP code; returns 0 if ready.
# Usage: syncyomi_ready "http://127.0.0.1:8282"
syncyomi_ready() {
	local base="$1" code
	code="$(curl -sS -o /dev/null -w '%{http_code}' "${base}/api/auth/onboard" 2>/dev/null || true)"
	echo "${code}"
	[[ ${code} == "204" || ${code} == "403" ]]
}

# --- Step 4: wait until the local API answers --------------------------------
wait_for_syncyomi() {
	log_info "Waiting for SyncYomi to come up on ${SYNCYOMI_LOCAL}"
	local i
	for ((i = 0; i < 60; i++)); do
		if syncyomi_ready "${SYNCYOMI_LOCAL}" >/dev/null; then
			log_ok "SyncYomi is up (API answering)"
			return 0
		fi
		sleep 2
	done
	die "SyncYomi did not become healthy in 120s — check 'docker logs syncyomi'."
}

# Defensive: SyncYomi generates config/config.toml on first run. Ensure it binds
# loopback-only (never 0.0.0.0, which would bypass Caddy/TLS) and serves at root.
ensure_local_config() {
	[[ -f ${CONFIG_TOML} ]] || return 0
	local changed=0
	if grep -qE '^\s*host\s*=' "${CONFIG_TOML}"; then
		if ! grep -qE '^\s*host\s*=\s*"127\.0\.0\.1"' "${CONFIG_TOML}"; then
			sed -i -E 's|^\s*host\s*=.*|host = "127.0.0.1"|' "${CONFIG_TOML}"
			changed=1
		fi
	fi
	# Force an empty baseUrl (dedicated subdomain, not a sub-path).
	if grep -qE '^\s*baseUrl\s*=' "${CONFIG_TOML}" &&
		! grep -qE '^\s*baseUrl\s*=\s*""' "${CONFIG_TOML}"; then
		sed -i -E 's|^\s*baseUrl\s*=.*|baseUrl = ""|' "${CONFIG_TOML}"
		changed=1
	fi
	if [[ ${changed} -eq 1 ]]; then
		log_info "Patched ${CONFIG_TOML} (host=127.0.0.1, baseUrl empty) — restarting"
		docker compose -f "${COMPOSE_FILE}" restart
		wait_for_syncyomi
	fi
}

# --- Step 5: create first account + mint API key over the local REST API -----
mint_api_key() {
	if [[ -f ${TOKEN_FILE} ]]; then
		log_ok "API key already minted ($(<"${TOKEN_FILE}") stored in ${TOKEN_FILE})"
		return 0
	fi
	log_info "Creating SyncYomi account and minting API key"

	local jar body http key
	jar="$(mktemp)"
	# shellcheck disable=SC2064
	trap "rm -f '${jar}'" RETURN

	# JSON with proper escaping (password may contain +,/,= from base64).
	body="$(jq -n --arg u "${SYNCYOMI_USER}" --arg p "${SYNCYOMI_PASSWORD}" \
		'{username:$u,password:$p}')"

	# Onboard the first user only if none exists yet (GET returns 204 when empty).
	http="$(curl -fsS -o /dev/null -w '%{http_code}' "${SYNCYOMI_LOCAL}/api/auth/onboard" 2>/dev/null || true)"
	if [[ ${http} == "204" ]]; then
		http="$(curl -sS -o /dev/null -w '%{http_code}' \
			-H 'Content-Type: application/json' -d "${body}" \
			"${SYNCYOMI_LOCAL}/api/auth/onboard" 2>/dev/null || true)"
		[[ ${http} =~ ^2 ]] || die "Onboard failed (HTTP ${http}) — check 'docker logs syncyomi'."
		log_ok "Created first account '${SYNCYOMI_USER}'"
	else
		log_warn "An account already exists (onboard HTTP ${http}); trying stored credentials"
	fi

	# Log in to get a session cookie.
	http="$(curl -sS -c "${jar}" -o /dev/null -w '%{http_code}' \
		-H 'Content-Type: application/json' -d "${body}" \
		"${SYNCYOMI_LOCAL}/api/auth/login" 2>/dev/null || true)"
	if [[ ! ${http} =~ ^2 ]]; then
		log_warn "Login failed (HTTP ${http}). A different account may already own this server."
		log_warn "Create an API key manually at ${SYNCYOMI_LOCAL} → Settings → API Keys."
		return 0
	fi

	# Reuse an existing 'tachiyomisy' key if one exists (idempotent); otherwise
	# create one. scopes must be a non-empty array — SyncYomi rejects a null.
	key="$(curl -sS -b "${jar}" "${SYNCYOMI_LOCAL}/api/keys" 2>/dev/null |
		jq -r '[.[] | select(.name=="tachiyomisy")][0].key // empty')"
	if [[ -n ${key} ]]; then
		log_ok "Reusing existing 'tachiyomisy' API key"
	else
		key="$(curl -sS -b "${jar}" \
			-H 'Content-Type: application/json' \
			-d '{"name":"tachiyomisy","scopes":["read","write"]}' \
			"${SYNCYOMI_LOCAL}/api/keys" 2>/dev/null | jq -r '.key // empty')"
		[[ -n ${key} ]] || die "API key creation returned no key — check 'docker logs syncyomi'."
	fi

	umask 077
	printf '%s\n' "${key}" >"${TOKEN_FILE}"
	chmod 600 "${TOKEN_FILE}"
	log_ok "Minted API key and stored it in ${TOKEN_FILE} (0600)"
}

# --- Step 6: Caddy reverse-proxy block (append + reload) ---------------------
configure_caddy() {
	if grep -qE "^${SYNCYOMI_SUBDOMAIN} \{" "${CADDYFILE}"; then
		log_ok "Caddyfile already has a block for ${SYNCYOMI_SUBDOMAIN}"
	else
		log_info "Adding Caddy block for ${SYNCYOMI_SUBDOMAIN}"
		# NOTE: appended to the shared Gitea Caddyfile. Re-running setup_gitea.sh
		# regenerates that file and drops this block — re-run setup_syncyomi.sh
		# to restore it. Caddyfile uses tab indentation.
		printf '\n%s {\n\treverse_proxy 127.0.0.1:%s\n}\n' "${SYNCYOMI_SUBDOMAIN}" "${SYNCYOMI_PORT}" \
			>>"${CADDYFILE}"
	fi
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

main() {
	local cmd="${1:-setup}"
	case "${cmd}" in
	setup) setup_cmd ;;
	status) status_cmd ;;
	help | -h | --help) usage ;;
	*) die "Unknown command '${cmd}' (use: setup | status | help)" ;;
	esac
}

main "$@"

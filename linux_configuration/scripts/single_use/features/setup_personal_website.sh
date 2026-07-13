#!/bin/bash
#
# setup_personal_website.sh — self-hosted personal website at kuhy.duckdns.org
#
# Builds the React/TypeScript personal website (projects showcase + CV) and
# serves its static build behind the existing shared Caddy edge (gitea-caddy),
# taking the bare root domain kuhy.duckdns.org. Gitea, which used to own that
# root, is moved to gitea.kuhy.duckdns.org.
#
# What it does (idempotent — safe to re-run):
#   - Installs build/runtime deps (node, pnpm, docker, ...).
#   - Migrates the shared Caddyfile to a per-service snippet directory so no
#     service block ever clobbers another (fixes a latent bug where re-running
#     setup_gitea.sh dropped the dufs/syncyomi blocks).
#   - Moves Gitea to gitea.kuhy.duckdns.org via setup_gitea.sh (single source).
#   - Builds the website and serves dist/ from a loopback caddy container on
#     127.0.0.1:8088, fronted by a reverse-proxy snippet on the root domain.
#   - Reuses the existing DuckDNS updater (wildcard already resolves) and opens
#     the firewall via setup_wireguard_ssh.sh.
#
# Reboot survival: the website container uses restart: unless-stopped and
# docker.service is enabled — no systemd unit is needed.
#
# Usage:
#   setup_personal_website.sh [setup]   Build + deploy (default).
#   setup_personal_website.sh status    Self-diagnose the deployment.
#   setup_personal_website.sh help      Show this help.
#
# Prerequisite: setup_gitea.sh must have been run at least once (the gitea-caddy
# edge must exist). Run as your normal user, not root.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
# shellcheck source=../../lib/common.sh
source "${SCRIPT_DIR}/../../lib/common.sh"

# --- Configuration ----------------------------------------------------------
readonly WEBSITE_DOMAIN="kuhy.duckdns.org"
readonly GITEA_DOMAIN="gitea.kuhy.duckdns.org"
readonly WEBSITE_PORT="8088"
# React/TS source lives in its own standalone repo (github.com/kuhyx/personal-website),
# cloned at ~/personal-website; the runtime data dir holds the generated compose +
# inner Caddyfile.
readonly WEBSITE_SRC="${HOME}/personal-website"
readonly WEBSITE_DATA_DIR="${HOME}/personal-website-serve"
readonly WEBSITE_COMPOSE="${WEBSITE_DATA_DIR}/docker-compose.yml"
readonly WEBSITE_INNER_CADDY="${WEBSITE_DATA_DIR}/Caddyfile"
# Shared edge owned by setup_gitea.sh.
readonly GITEA_DATA_DIR="${HOME}/gitea"
readonly CADDYFILE="${GITEA_DATA_DIR}/Caddyfile"
readonly SITES_DIR="${GITEA_DATA_DIR}/sites"
readonly WEBSITE_SNIPPET="${SITES_DIR}/website.caddy"
readonly CADDY_CONTAINER="gitea-caddy"
# Sibling scripts (single sources of truth for their concerns).
readonly GITEA_SCRIPT="${SCRIPT_DIR}/setup_gitea.sh"
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"
# Canonical CV data (rendered by the CV repo's build_cv.py); copied into the
# website build. A committed copy in the repo keeps the build standalone.
readonly CV_JSON_SRC="${HOME}/CV/generic/cv.json"
readonly CV_PDF_SRC="${HOME}/CV/generic/cv-en.pdf"

die() {
	log_error "$1"
	exit 1
}

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit 0
}

# --- Phase 1: preflight -----------------------------------------------------
preflight() {
	[[ ${EUID} -ne 0 ]] || die "Run as your normal user, not root."
	[[ -d $WEBSITE_SRC ]] || die "Website source not found at ${WEBSITE_SRC}."

	install_missing_pacman_packages nodejs pnpm docker docker-compose jq curl

	if ! is_service_active docker; then
		log_info "Starting and enabling docker.service…"
		sudo systemctl enable --now docker
	fi

	[[ -f $CADDYFILE ]] ||
		die "Shared Caddyfile ${CADDYFILE} missing — run setup_gitea.sh first."
	if ! docker ps --format '{{.Names}}' | grep -qx "$CADDY_CONTAINER"; then
		die "Container ${CADDY_CONTAINER} is not running — run setup_gitea.sh first."
	fi
	log_ok "Preflight checks passed."
}

# --- Phase 2: migrate the shared Caddyfile into per-service snippets ---------
# Reads the CURRENT monolithic Caddyfile and writes every top-level block to
# sites/<label>.caddy, EXCEPT the old root block (kuhy.duckdns.org, previously
# gitea — now repurposed for the website) and the gitea block (setup_gitea.sh
# rewrites its own). This preserves dufs (kuhy-cloud) and syncyomi (kuhy-sync)
# before setup_gitea.sh switches the root Caddyfile to `import`. Idempotent.
migrate_caddy_snippets() {
	ensure_dir "$SITES_DIR"
	if grep -qE '^[[:space:]]*import[[:space:]]+/etc/caddy/sites' "$CADDYFILE"; then
		log_info "Caddyfile already uses per-service snippets; nothing to migrate."
		return 0
	fi

	local line label body in_block=0 migrated=0
	label=""
	body=""
	while IFS= read -r line || [[ -n $line ]]; do
		if [[ $in_block -eq 0 && $line =~ ^([^[:space:]#].*)\{[[:space:]]*$ ]]; then
			label="${BASH_REMATCH[1]}"
			# Trim trailing whitespace from the captured label.
			label="${label%"${label##*[![:space:]]}"}"
			body="${line}"$'\n'
			in_block=1
		elif [[ $in_block -eq 1 ]]; then
			body+="${line}"$'\n'
			if [[ $line =~ ^\}[[:space:]]*$ ]]; then
				in_block=0
				if [[ $label == "$WEBSITE_DOMAIN" || $label == "$GITEA_DOMAIN" ]]; then
					label=""
					body=""
					continue
				fi
				local snippet="${SITES_DIR}/${label}.caddy"
				if [[ ! -f $snippet ]]; then
					printf '# Migrated from Caddyfile by setup_personal_website.sh\n%s' \
						"$body" >"$snippet"
					log_ok "Migrated ${label} → ${snippet}"
					migrated=$((migrated + 1))
				fi
				label=""
				body=""
			fi
		fi
	done <"$CADDYFILE"
	log_info "Migrated ${migrated} existing site block(s) into ${SITES_DIR}."
}

# --- Phase 3: relocate Gitea to its subdomain -------------------------------
relocate_gitea() {
	log_info "Applying Gitea relocation to ${GITEA_DOMAIN} via setup_gitea.sh…"
	bash "$GITEA_SCRIPT" setup
	log_ok "Gitea now served at https://${GITEA_DOMAIN}/."
}

# --- Phase 4: refresh CV data ----------------------------------------------
build_cv_json() {
	if [[ -f $CV_JSON_SRC ]]; then
		cp "$CV_JSON_SRC" "${WEBSITE_SRC}/src/data/cv.json"
		log_ok "Copied CV data from ${CV_JSON_SRC}."
	else
		log_warn "CV data ${CV_JSON_SRC} not found — using the copy committed in the website repo."
	fi
	# Stage the rendered PDF for the CV download button (served from /cv.pdf).
	if [[ -f $CV_PDF_SRC ]]; then
		ensure_dir "${WEBSITE_SRC}/public"
		cp "$CV_PDF_SRC" "${WEBSITE_SRC}/public/cv.pdf"
		log_ok "Copied CV PDF from ${CV_PDF_SRC}."
	else
		log_warn "CV PDF ${CV_PDF_SRC} not found — the Download PDF link will 404 until built."
	fi
}

# --- Phase 5: build the website --------------------------------------------
build_website() {
	log_info "Installing website dependencies and building…"
	(
		cd "$WEBSITE_SRC"
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
	try_files {path} /index.html
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
wait_for_website() {
	local _
	for _ in $(seq 1 30); do
		if curl -sf -o /dev/null "http://127.0.0.1:${WEBSITE_PORT}/"; then
			return 0
		fi
		sleep 1
	done
	return 1
}

start_website() {
	log_info "Starting the personal-website container…"
	docker compose -f "$WEBSITE_COMPOSE" up -d
	if wait_for_website; then
		log_ok "Website answering on http://127.0.0.1:${WEBSITE_PORT}/."
	else
		die "Website did not become reachable on 127.0.0.1:${WEBSITE_PORT}."
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

	has_cmd node && status_line 0 "node present" || status_line 1 "node missing"
	has_cmd pnpm && status_line 0 "pnpm present" || status_line 1 "pnpm missing"

	[[ -f "${WEBSITE_SRC}/dist/index.html" ]] &&
		status_line 0 "build present (dist/index.html)" ||
		status_line 1 "build missing — run setup"

	if docker ps --format '{{.Names}}' | grep -qx personal-website; then
		status_line 0 "personal-website container running"
	else
		status_line 1 "personal-website container not running"
	fi

	status_line "$(check_http "http://127.0.0.1:${WEBSITE_PORT}/")" \
		"local static server (127.0.0.1:${WEBSITE_PORT})"

	[[ -f $WEBSITE_SNIPPET ]] &&
		status_line 0 "Caddy website snippet present" ||
		status_line 1 "Caddy website snippet missing"
	grep -qE '^[[:space:]]*import[[:space:]]+/etc/caddy/sites' "$CADDYFILE" 2>/dev/null &&
		status_line 0 "root Caddyfile uses snippet imports" ||
		status_line 1 "root Caddyfile not migrated to imports"

	getent hosts "$WEBSITE_DOMAIN" >/dev/null &&
		status_line 0 "${WEBSITE_DOMAIN} resolves" ||
		status_line 1 "${WEBSITE_DOMAIN} does not resolve"
	getent hosts "$GITEA_DOMAIN" >/dev/null &&
		status_line 0 "${GITEA_DOMAIN} resolves" ||
		status_line 1 "${GITEA_DOMAIN} does not resolve"

	status_line "$(check_http "https://${WEBSITE_DOMAIN}/")" \
		"external https://${WEBSITE_DOMAIN}/"
	status_line "$(check_http "https://${GITEA_DOMAIN}/")" \
		"external https://${GITEA_DOMAIN}/"
}

main() {
	local cmd="${1:-setup}"
	case "$cmd" in
	setup)
		setup_cmd
		;;
	status)
		status_cmd
		;;
	help | -h | --help)
		usage
		;;
	*)
		log_error "Unknown command: $cmd"
		usage
		exit 1
		;;
	esac
}

main "$@"

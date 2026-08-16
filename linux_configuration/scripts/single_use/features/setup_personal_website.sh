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

# Takes the exit status to leave with, so the error path can print the same help
# and still fail. It used to hardcode `exit 0`, which made the `exit 1` after the
# unknown-command branch unreachable -- so `setup_personal_website.sh bogus`
# printed an error and then reported SUCCESS to its caller.
usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit "${1:-0}"
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

# shellcheck source=lib/website_build.sh
source "$SCRIPT_DIR/lib/website_build.sh"

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
		usage 1
		;;
	esac
}

main "$@"

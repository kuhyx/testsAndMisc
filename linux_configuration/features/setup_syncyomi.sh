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

# --- SyncYomi image ----------------------------------------------------------
# Runs a local build of the personal fork by default, so server-side changes
# actually reach the service instead of sitting unbuilt in a clone. The
# published image stays one variable away:
#   SYNCYOMI_IMAGE=ghcr.io/syncyomi/syncyomi:v1.1.11 ./setup_syncyomi.sh
# Any value containing a "/" is treated as a registry image and pulled as-is.
readonly SYNCYOMI_IMAGE="${SYNCYOMI_IMAGE:-syncyomi-kuhy:local}"
readonly SYNCYOMI_SRC="${SYNCYOMI_SRC:-${HOME}/syncyomi-src}"
readonly SYNCYOMI_FORK_URL="https://github.com/kuhyx/syncyomi.git"
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
readonly CADDY_SITES_DIR="${HOME}/gitea/sites"
readonly CADDYFILE_IN_CONTAINER="/etc/caddy/Caddyfile"
readonly DUCKDNS_UPDATER="${HOME}/.joplin-server/duckdns-update.sh"

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"

# shellcheck source=../lib/common.sh
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

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
	# docker-buildx: the fork's Dockerfile uses $BUILDPLATFORM, which only the
	# BuildKit builder defines; the legacy builder rejects the empty value.
	install_missing_pacman_packages docker docker-compose jq curl openssl git docker-buildx

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

# shellcheck source=lib/syncyomi_stack.sh
source "$SCRIPT_DIR/lib/syncyomi_stack.sh"
# shellcheck source=lib/syncyomi_expose.sh
source "$SCRIPT_DIR/lib/syncyomi_expose.sh"

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

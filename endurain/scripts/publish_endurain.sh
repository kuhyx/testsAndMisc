#!/bin/bash

# ============================================================================
# Publish Endurain on the shared Caddy edge (endurain.kuhy.duckdns.org).
#
# Split out of setup_endurain.sh deliberately. endurain.kuhy.duckdns.org
# already resolves to this host via the duckdns wildcard on "kuhy", so
# installing the site snippet makes the service world-reachable the moment
# Caddy reloads. Endurain ships a hardcoded admin/admin account seeded by an
# Alembic migration with no environment override, so publishing before that
# password is changed hands the internet an admin login.
#
# This script therefore re-runs the same gate and REFUSES to publish while the
# seeded credentials still work.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly APP_URL="http://127.0.0.1:8085"
readonly PUBLIC_HOST="endurain.kuhy.duckdns.org"
readonly EDGE_DIR="${HOME}/gitea"
readonly SITE_FILE="${EDGE_DIR}/sites/endurain.caddy"
readonly EDGE_CONTAINER="gitea-caddy"

log() { printf '%s\n' "$*"; }
log_ok() { printf '  ok: %s\n' "$*"; }
die() {
	printf 'Error: %s\n' "$*" >&2
	exit 1
}

usage() {
	echo "Usage: ${SCRIPT_NAME}"
	echo "  Installs the Caddy site for ${PUBLIC_HOST} and reloads the edge."
	exit 0
}

# Fail closed. Only an explicit rejection counts as "safe"; any unexpected
# status is treated as still-vulnerable.
assert_admin_password_changed() {
	local code
	code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 \
		-X POST "${APP_URL}/api/v1/auth/login" \
		-H 'Content-Type: application/x-www-form-urlencoded' \
		-H 'X-Client-Type: mobile' \
		--data 'username=admin&password=admin' 2>/dev/null || echo 000)"
	case "${code}" in
	401 | 403) log_ok "seeded admin/admin is rejected" ;;
	200) die "REFUSING TO PUBLISH: Endurain still accepts admin/admin.
   Change it at ${APP_URL} first." ;;
	*) die "REFUSING TO PUBLISH: unexpected status ${code} from the login
   probe; cannot prove the seeded password was changed." ;;
	esac
}

validate_requirements() {
	command -v docker >/dev/null || die "docker not installed"
	[[ -d "${EDGE_DIR}/sites" ]] || die "Caddy edge not found at ${EDGE_DIR}/sites"
	docker ps --format '{{.Names}}' | grep -qx "${EDGE_CONTAINER}" ||
		die "${EDGE_CONTAINER} is not running"
	curl -fsS --max-time 5 "${APP_URL}/api/v1/about" >/dev/null ||
		die "Endurain is not responding on ${APP_URL}"
}

install_site() {
	cat >"${SITE_FILE}" <<EOF
# Managed by ${SCRIPT_NAME} — do not edit by hand.
${PUBLIC_HOST} {
	reverse_proxy 127.0.0.1:8085
}
EOF
	log_ok "Wrote ${SITE_FILE}"
}

reload_edge() {
	# Validate before reloading so a broken snippet cannot take the whole edge
	# (gitea, the cloud, the website) down with it.
	docker exec "${EDGE_CONTAINER}" caddy validate --config /etc/caddy/Caddyfile \
		>/dev/null 2>&1 || die "Caddy config failed validation; edge NOT reloaded"
	docker exec "${EDGE_CONTAINER}" caddy reload --config /etc/caddy/Caddyfile \
		>/dev/null || die "caddy reload failed"
	log_ok "Edge reloaded"
}

main() {
	validate_requirements
	assert_admin_password_changed
	install_site
	reload_edge
	log ""
	log "Published: https://${PUBLIC_HOST}"
	log "Caddy obtains the certificate on the first request; allow a few seconds."
}

while [[ $# -gt 0 ]]; do
	case $1 in
	-h | --help) usage ;;
	*) die "Unknown option: $1" ;;
	esac
done

main "$@"

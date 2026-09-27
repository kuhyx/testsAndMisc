#!/bin/bash
#
# setup_homeassistant.sh — Home Assistant on this PC, for LAN-local control of
# the Viomi V3 robot vacuum (viomi.vacuum.v13) and anything added later.
#
# What it does (idempotent — safe to re-run):
#   - Writes ~/services/homeassistant/docker-compose.yml and runs HA with
#     network_mode: host (bridge containers have no egress on this host; see
#     setup_searxng.sh for the nftables reason), listening on :8123.
#   - Installs the al-one/hass-xiaomi-miot custom integration at a pinned tag
#     into config/custom_components/xiaomi_miot (MIoT over LAN; HA core's own
#     xiaomi_miio does not know viomi.vacuum.v13).
#   - Waits until the HTTP API answers.
#
# Reachability: 8123 is opened to the LAN and wg0 only, by
#   sudo setup_wireguard_ssh.sh allow-homeassistant
# (the firewall's single source of truth). `status` checks that rule.
#
# Usage:
#   setup_homeassistant.sh [setup]   Deploy (default).
#   setup_homeassistant.sh status    Self-diagnose the deployment.
#   setup_homeassistant.sh help      Show this help.
#
# Run as your normal user, not root.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

# --- Configuration ----------------------------------------------------------
readonly HA_PORT="8123"
# home-assistant 2026.9.4 (newest stable on 2026-09-27), pinned by digest so a
# re-run never silently upgrades. To upgrade: change digest + comment, re-run.
readonly HA_IMAGE="ghcr.io/home-assistant/home-assistant@sha256:3e6710a7ab2a61311d9d899b719f6c3657791c63e8f4942cec4ebc42401d6b76"
readonly HA_CONTAINER="homeassistant"
# hass-xiaomi-miot newest stable on 2026-09-27. Issue #2677 (send_command via
# Developer tools broken since v1.1.0) is still open; vacuum start/dock go
# through entity services, not that path.
readonly MIOT_VERSION="v1.1.5"
readonly MIOT_REPO="al-one/hass-xiaomi-miot"
readonly HA_DIR="${HOME}/services/homeassistant"
readonly HA_COMPOSE="${HA_DIR}/docker-compose.yml"
readonly HA_CONFIG="${HA_DIR}/config"
readonly MIOT_DIR="${HA_CONFIG}/custom_components/xiaomi_miot"
readonly MIOT_STAMP="${MIOT_DIR}/.installed_version"

TMP_DIR=""
cleanup() {
	if [[ -n ${TMP_DIR} && -d ${TMP_DIR} ]]; then
		rm -rf "${TMP_DIR}"
	fi
}
trap cleanup EXIT

die() {
	log_error "$1"
	exit 1
}

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit "${1:-0}"
}

preflight() {
	[[ ${EUID} -ne 0 ]] || die "Run as your normal user, not root."
	install_missing_pacman_packages docker docker-compose curl tar
	is_service_active docker || die "docker.service is not running."
	# A foreign listener on 8123 is fatal; our own container is a re-run.
	if ss -ltn 2>/dev/null | grep -qE "[:.]${HA_PORT}[[:space:]]" &&
		! docker ps --format '{{.Names}}' | grep -qx "${HA_CONTAINER}"; then
		die "Port ${HA_PORT} is taken by something other than ${HA_CONTAINER}."
	fi
}

write_compose() {
	mkdir -p "${HA_CONFIG}"
	cat >"${HA_COMPOSE}" <<EOF
# Managed by setup_homeassistant.sh — do not edit by hand.
services:
  homeassistant:
    container_name: ${HA_CONTAINER}
    image: ${HA_IMAGE}
    network_mode: host
    restart: unless-stopped
    environment:
      - TZ=Europe/Warsaw
    volumes:
      - ${HA_CONFIG}:/config
EOF
	log_ok "Wrote ${HA_COMPOSE}"
}

install_miot() {
	if [[ -f ${MIOT_STAMP} && "$(<"${MIOT_STAMP}")" == "${MIOT_VERSION}" ]]; then
		log_ok "xiaomi_miot ${MIOT_VERSION} already installed."
		return 0
	fi
	TMP_DIR="$(mktemp -d)"
	curl -fsSL "https://github.com/${MIOT_REPO}/archive/refs/tags/${MIOT_VERSION}.tar.gz" |
		tar -xz -C "${TMP_DIR}"
	local src
	src="$(find "${TMP_DIR}" -maxdepth 3 -type d -path '*/custom_components/xiaomi_miot' | head -1)"
	[[ -n ${src} ]] || die "custom_components/xiaomi_miot not found in ${MIOT_VERSION} tarball."
	rm -rf "${MIOT_DIR}"
	mkdir -p "$(dirname "${MIOT_DIR}")"
	cp -r "${src}" "${MIOT_DIR}"
	printf '%s' "${MIOT_VERSION}" >"${MIOT_STAMP}"
	log_ok "Installed xiaomi_miot ${MIOT_VERSION} into ${MIOT_DIR}"
}

wait_for_api() {
	local code="" i
	for ((i = 0; i < 60; i++)); do
		code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${HA_PORT}/api/" || true)"
		# 401 = API up and demanding auth; 200 = onboarding not done yet.
		[[ ${code} == 401 || ${code} == 200 ]] && break
		sleep 2
	done
	[[ ${code} == 401 || ${code} == 200 ]] || die "HA API did not come up (last HTTP ${code:-none})."
	log_ok "HA answers on http://127.0.0.1:${HA_PORT} (HTTP ${code})."
}

setup_cmd() {
	preflight
	write_compose
	install_miot
	docker compose -f "${HA_COMPOSE}" up -d
	# A freshly copied custom component is only loaded at start.
	docker restart "${HA_CONTAINER}" >/dev/null
	wait_for_api
	log_info "Open http://<this-PC-LAN-IP>:${HA_PORT} from the phone app."
}

status_cmd() {
	local rc=0 state code
	state="$(docker inspect -f '{{.State.Status}}' "${HA_CONTAINER}" 2>/dev/null || echo absent)"
	if [[ ${state} == running ]]; then
		log_ok "container: ${state}"
	else
		log_error "container: ${state}"
		rc=1
	fi
	code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${HA_PORT}/api/" || true)"
	if [[ ${code} == 401 || ${code} == 200 ]]; then
		log_ok "API: HTTP ${code}"
	else
		log_error "API: HTTP ${code:-none}"
		rc=1
	fi
	if [[ -f ${MIOT_STAMP} ]]; then
		log_ok "xiaomi_miot: $(<"${MIOT_STAMP}") (want ${MIOT_VERSION})"
	else
		log_error "xiaomi_miot: not installed"
		rc=1
	fi
	if sudo -n nft list chain inet filter input 2>/dev/null | grep -q "dport ${HA_PORT} accept"; then
		log_ok "firewall: tcp/${HA_PORT} open to LAN/wg0"
	else
		log_warn "firewall: no tcp/${HA_PORT} rule (or no sudo) — sudo setup_wireguard_ssh.sh allow-homeassistant"
	fi
	return "${rc}"
}

main() {
	case "${1:-setup}" in
	setup) setup_cmd ;;
	status) status_cmd ;;
	help | -h | --help) usage 0 ;;
	*) usage 1 ;;
	esac
}

main "$@"

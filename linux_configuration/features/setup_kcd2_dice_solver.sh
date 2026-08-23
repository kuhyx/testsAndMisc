#!/bin/bash
#
# setup_kcd2_dice_solver.sh — KCD2 dice solver at dice.kuhy.duckdns.org
#
# Serves the solver's static build behind the existing shared Caddy edge
# (gitea-caddy), and wires up an auto-rebuild so committing to main republishes
# the site.
#
# No DuckDNS work is needed: DuckDNS wildcards *.kuhy.duckdns.org, verified
# against 1.1.1.1 and 8.8.8.8 (an unregistered zzz-nope-9x.kuhy.duckdns.org
# resolves to the same address). Adding the Caddy snippet is enough to get a
# certificate.
#
# What it does (idempotent — safe to re-run):
#   - Installs build/runtime deps.
#   - Builds dist/ via the repo's own deploy_build.sh.
#   - Serves dist/ read-only from a loopback caddy container on 127.0.0.1:8089.
#   - Adds a reverse-proxy snippet for dice.kuhy.duckdns.org to the shared edge.
#   - Installs a memory-capped systemd user unit plus a post-commit git hook so
#     commits to main that touch kcd2_dice_solver/ republish the site.
#   - Opens the firewall via setup_wireguard_ssh.sh (already open in practice).
#
# Reboot survival: the container uses restart: unless-stopped and docker.service
# is enabled — no systemd unit is needed for serving.
#
# Usage:
#   setup_kcd2_dice_solver.sh [setup]   Build + deploy (default).
#   setup_kcd2_dice_solver.sh status    Self-diagnose the deployment.
#   setup_kcd2_dice_solver.sh help      Show this help.
#
# Prerequisite: setup_gitea.sh must have been run at least once (the gitea-caddy
# edge must exist). Run as your normal user, not root.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

# --- Configuration ----------------------------------------------------------
readonly DICE_DOMAIN="dice.kuhy.duckdns.org"
readonly DICE_PORT="8089"
# The solver was extracted to its own repo; this script only deploys it.
readonly DICE_SRC="${HOME}/kcd2-dice-solver"
readonly REPO_ROOT="${DICE_SRC}"
readonly DICE_BUILD="${DICE_SRC}/deploy_build.sh"
readonly DICE_DATA_DIR="${HOME}/kcd2-dice-serve"
readonly DICE_COMPOSE="${DICE_DATA_DIR}/docker-compose.yml"
readonly DICE_INNER_CADDY="${DICE_DATA_DIR}/Caddyfile"
# Shared edge owned by setup_gitea.sh.
readonly GITEA_DATA_DIR="${HOME}/gitea"
readonly CADDYFILE="${GITEA_DATA_DIR}/Caddyfile"
readonly SITES_DIR="${GITEA_DATA_DIR}/sites"
readonly DICE_SNIPPET="${SITES_DIR}/dice.caddy"
readonly CADDY_CONTAINER="gitea-caddy"
readonly DICE_CONTAINER="kcd2-dice"
# Auto-rebuild.
readonly UNIT_DIR="${HOME}/.config/systemd/user"
readonly UNIT_NAME="kcd2-dice-build.service"
readonly UNIT_FILE="${UNIT_DIR}/${UNIT_NAME}"
readonly HOOK_FILE="${REPO_ROOT}/.git/hooks/post-commit"
# Sibling script (single source of truth for the firewall).
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"

die() {
	log_error "$1"
	exit 1
}

# Takes the exit status to leave with, so the error path can print the same
# help and still fail. Hardcoding `exit 0` made the `exit 1` after the
# unknown-command branch unreachable -- the script reported SUCCESS on a typo.
usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit "${1:-0}"
}

# --- Phase 1: preflight -----------------------------------------------------
preflight() {
	[[ ${EUID} -ne 0 ]] || die "Run as your normal user, not root."
	[[ -d $DICE_SRC ]] || die "Solver source not found at ${DICE_SRC}."
	[[ -x $DICE_BUILD ]] || die "Build script ${DICE_BUILD} is missing or not executable."

	install_missing_pacman_packages nodejs pnpm docker docker-compose rsync curl

	if ! is_service_active docker; then
		log_info "Starting and enabling docker.service…"
		sudo systemctl enable --now docker
	fi

	[[ -f $CADDYFILE ]] ||
		die "Shared Caddyfile ${CADDYFILE} missing — run setup_gitea.sh first."
	if ! docker ps --format '{{.Names}}' | grep -qx "$CADDY_CONTAINER"; then
		die "Container ${CADDY_CONTAINER} is not running — run setup_gitea.sh first."
	fi
	grep -qE '^[[:space:]]*import[[:space:]]+/etc/caddy/sites' "$CADDYFILE" ||
		die "Root Caddyfile does not import sites/ — run setup_personal_website.sh first."
	log_ok "Preflight checks passed."
}

# --- Phase 2: build ---------------------------------------------------------
build_solver() {
	log_info "Building the solver bundle…"
	bash "$DICE_BUILD"
	[[ -f "${DICE_SRC}/dist/index.html" ]] ||
		die "Build did not produce ${DICE_SRC}/dist/index.html."
	log_ok "Solver built to ${DICE_SRC}/dist."
}

# shellcheck source=lib/kcd2_serve.sh
source "$SCRIPT_DIR/lib/kcd2_serve.sh"
# shellcheck source=lib/kcd2_expose.sh
source "$SCRIPT_DIR/lib/kcd2_expose.sh"
# shellcheck source=lib/kcd2_autorebuild.sh
source "$SCRIPT_DIR/lib/kcd2_autorebuild.sh"

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

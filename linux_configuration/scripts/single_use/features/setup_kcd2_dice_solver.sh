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
# shellcheck source=../../lib/common.sh
source "${SCRIPT_DIR}/../../lib/common.sh"

# --- Configuration ----------------------------------------------------------
readonly DICE_DOMAIN="dice.kuhy.duckdns.org"
readonly DICE_PORT="8089"
readonly REPO_ROOT="${HOME}/testsAndMisc"
readonly DICE_SRC="${REPO_ROOT}/kcd2_dice_solver"
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

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit 0
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

# --- Phase 3: the static-serve stack ----------------------------------------
write_serve_stack() {
	ensure_dir "$DICE_DATA_DIR"
	cat >"$DICE_COMPOSE" <<EOF
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
services:
  ${DICE_CONTAINER}:
    image: caddy:2.8
    container_name: ${DICE_CONTAINER}
    restart: unless-stopped
    # host networking is REQUIRED, not a style choice: the nftables forward
    # chain is policy drop with no accept rules, so a bridge-networked
    # container has no outbound egress at all.
    network_mode: host
    volumes:
      - ${DICE_SRC}/dist:/srv:ro
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
EOF

	cat >"$DICE_INNER_CADDY" <<EOF
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
# Static file server on loopback; fronted by ${CADDY_CONTAINER} on the public
# domain.
#
# admin off is REQUIRED: this container shares the host network namespace with
# ${CADDY_CONTAINER}, so without it both would listen on the admin API (:2019)
# and a 'caddy reload' aimed at the edge could be applied here instead — which
# would make this process grab 80/443 and run its own ACME.
#
# auto_https off and the explicit http:// scheme are EQUALLY required, and this
# was found the hard way. A site address of "127.0.0.1:${DICE_PORT}" reads as a
# HOSTNAME, so Caddy turns on automatic HTTPS for it: it issues a local
# certificate, serves TLS on ${DICE_PORT} (so the plain-HTTP health check fails)
# and — the real damage — starts an HTTP->HTTPS redirect listener on :80. Under
# host networking that binds *:80 next to the edge, and SO_REUSEPORT then splits
# inbound HTTP between the two, which would intermittently break ACME
# challenges for every domain on this host.
#
# The site address is port-only and the loopback restriction is done with
# "bind". These are two different things and using the wrong one breaks in a way
# that looks like it works:
#
#   A site address of "http://127.0.0.1:${DICE_PORT}" sets a host MATCHER of
#   127.0.0.1. ${CADDY_CONTAINER} forwards the original "Host:
#   ${DICE_DOMAIN}" header, which then matches no route, and Caddy answers 200
#   with an empty body. A local health check passes (curl sends Host:
#   127.0.0.1) while every real request serves a blank page.
#
#   ":${DICE_PORT}" matches any Host, and "bind 127.0.0.1" restricts the
#   listener itself — which the address never did. Without bind, host
#   networking would expose this unfronted server to the whole LAN.
{
	admin off
	auto_https off
}

:${DICE_PORT} {
	bind 127.0.0.1
	root * /srv
	# Single-page bundle: unknown paths should serve the app, not 404.
	try_files {path} /index.html
	file_server
	encode gzip
}
EOF
	log_ok "Wrote ${DICE_COMPOSE} and ${DICE_INNER_CADDY}."
}

# --- Phase 4: front it on the public domain ---------------------------------
write_snippet() {
	cat >"$DICE_SNIPPET" <<EOF
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
${DICE_DOMAIN} {
	reverse_proxy 127.0.0.1:${DICE_PORT}
}
EOF
	log_ok "Wrote ${DICE_SNIPPET}."
}

# --- Phase 5: start ---------------------------------------------------------
# Sends the Host header the edge will actually forward, and requires a
# non-empty body. A bare "curl http://127.0.0.1:PORT/" sends Host: 127.0.0.1
# and returns an empty 200 against a host-matcher misconfiguration — it passes
# while every real request serves a blank page. Ask the question the edge asks.
wait_for_site() {
	local _ size
	for _ in $(seq 1 30); do
		size="$(curl -s -o /dev/null -w '%{size_download}' \
			-H "Host: ${DICE_DOMAIN}" "http://127.0.0.1:${DICE_PORT}/" 2>/dev/null || echo 0)"
		if [[ ${size:-0} -gt 0 ]]; then
			return 0
		fi
		sleep 1
	done
	return 1
}

# This container shares the host network namespace with the public edge, so a
# misconfiguration here does not fail locally — it quietly steals a share of
# :80 or :443 from every other site on the box. Gate on it rather than trust
# the config to stay correct.
assert_no_edge_conflict() {
	local pid listeners
	pid="$(docker inspect -f '{{.State.Pid}}' "$DICE_CONTAINER" 2>/dev/null || echo "")"
	[[ -n $pid && $pid != "0" ]] || die "Could not read the ${DICE_CONTAINER} PID."

	listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"

	# Demand positive evidence FIRST. Asserting only the absence of :80/:443
	# fails open: if `ss` returns nothing — a stale PID after a restart, or
	# sudo -n unavailable — every "is it bad?" test misses and the guard happily
	# reports success without having looked at anything.
	if ! grep -qE '(^|[[:space:]])127\.0\.0\.1:'"${DICE_PORT}"'([[:space:]]|$)' <<<"$listeners"; then
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "Could not confirm ${DICE_CONTAINER} listens on 127.0.0.1:${DICE_PORT}. Container stopped."
	fi
	if grep -qE ':(80|443)\b' <<<"$listeners"; then
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "${DICE_CONTAINER} bound :80/:443 — it would contend with ${CADDY_CONTAINER}. Container stopped."
	fi
	# Must be on loopback, not 0.0.0.0/*: host networking would otherwise expose
	# the unfronted static server to the whole LAN.
	if grep -qE '(\*|0\.0\.0\.0):'"${DICE_PORT}"'\b' <<<"$listeners"; then
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "${DICE_CONTAINER} bound ${DICE_PORT} on all interfaces, not loopback. Container stopped."
	fi
	log_ok "${DICE_CONTAINER} listens on loopback:${DICE_PORT} only — no contention, not LAN-exposed."
}

start_site() {
	log_info "Starting the ${DICE_CONTAINER} container…"
	docker compose -f "$DICE_COMPOSE" up -d
	if wait_for_site; then
		log_ok "Solver answering on http://127.0.0.1:${DICE_PORT}/."
	else
		docker stop "$DICE_CONTAINER" >/dev/null 2>&1 || true
		die "Solver did not become reachable on 127.0.0.1:${DICE_PORT} (container stopped)."
	fi
	assert_no_edge_conflict
}

# --- Phase 6: reload the edge -----------------------------------------------
reload_caddy() {
	if docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
		docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
		log_ok "Reloaded ${CADDY_CONTAINER}."
	else
		die "Caddy config invalid — aborting reload. Check ${SITES_DIR}/*.caddy."
	fi
}

# --- Phase 7: auto-rebuild on commit ----------------------------------------
# The build runs in a memory-capped systemd user unit rather than inside the
# git hook. MemorySwapMax=0 is required, not cosmetic: this box has ~4 GB of
# zram (swap held IN ram), so a memory-limited cgroup without it thrashes zram
# instead of dying cleanly, and freezes the machine. A git hook running tsc and
# vite is precisely the scenario that costs.
install_autorebuild() {
	ensure_dir "$UNIT_DIR"
	cat >"$UNIT_FILE" <<EOF
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
[Unit]
Description=Rebuild the KCD2 dice solver static bundle

[Service]
Type=oneshot
WorkingDirectory=${DICE_SRC}
ExecStart=${DICE_BUILD}
MemoryMax=3G
MemorySwapMax=0
EOF
	systemctl --user daemon-reload
	log_ok "Installed ${UNIT_FILE}."

	[[ -d "${REPO_ROOT}/.git" ]] || die "${REPO_ROOT} is not a git repository."
	cat >"$HOOK_FILE" <<EOF
#!/bin/bash
# Managed by setup_kcd2_dice_solver.sh — do not edit by hand.
# Republishes https://${DICE_DOMAIN}/ when main gains solver changes.
[[ "\$(git rev-parse --abbrev-ref HEAD)" == main ]] || exit 0
git diff --name-only HEAD~1 HEAD -- kcd2_dice_solver/ | grep -q . || exit 0
# --no-block so the commit is never slowed, || true so systemd can never fail it.
systemctl --user start --no-block ${UNIT_NAME} || true
EOF
	chmod +x "$HOOK_FILE"
	log_ok "Installed ${HOOK_FILE}."
}

# --- Phase 8: firewall ------------------------------------------------------
# setup_wireguard_ssh.sh owns /etc/nftables.conf and regenerates it from
# scratch — `flush ruleset` and all — on every run. That is fine on a quiet
# machine and rude on a busy one: it momentarily drops the whole ruleset while
# games, VPN links and long-lived connections are relying on it. Since the only
# thing this deployment needs is 80/443 already being accepted, check first and
# only pay for the regeneration when the rule is genuinely missing.
# Exact token membership rather than a regex over the rule text: a loose
# pattern would also match "8080, 4433" and wrongly conclude the ports are open.
web_ports_open() {
	local line ports
	while read -r line; do
		# Strip everything but digits and commas, then test for whole tokens.
		ports=",${line//[^0-9,]/},"
		if [[ $ports == *,80,* && $ports == *,443,* ]]; then
			return 0
		fi
	done < <(sudo -n nft list ruleset 2>/dev/null | grep -oE 'tcp dport \{[^}]*\}')
	return 1
}

ensure_firewall() {
	if web_ports_open; then
		log_ok "Ports 80/443 already accepted — leaving the ruleset untouched."
		return 0
	fi
	log_info "Opening ports 80/443 via setup_wireguard_ssh.sh…"
	sudo bash "$WG_SCRIPT" allow-web
}

# --- Phase 9: report --------------------------------------------------------
print_report() {
	cat <<EOF

============================================================================
KCD2 dice solver deployed.
============================================================================
  Solver : https://${DICE_DOMAIN}/

Auto-rebuild: committing to main with changes under kcd2_dice_solver/ starts
${UNIT_NAME}, which rebuilds dist/ in place.
  Watch it:  journalctl --user -u ${UNIT_NAME} -f
  Force it:  systemctl --user start ${UNIT_NAME}

NOTE: the rebuild builds the WORKING TREE, not the commit. An unrelated
uncommitted edit that happens to be present when it runs will ship to the live
site. Commit or set aside unrelated work before triggering a rebuild.

Acceptance test (do this on your phone):
  Turn Wi-Fi OFF (use cellular) and open https://${DICE_DOMAIN}/ —
  all 43 dice should be on one screen and tappable.
============================================================================
EOF
}

setup_cmd() {
	print_setup_header "KCD2 dice solver setup"
	preflight
	build_solver
	write_serve_stack
	# The snippet goes into the SHARED sites/ directory, so it is written only
	# after the backend is up and verified. Writing it first means a failure in
	# start_site leaves an orphan behind that the next `caddy reload` from any
	# other service picks up — the edge then serves this domain as a 502 and
	# starts ACME retries for a host with no backend.
	start_site
	write_snippet
	reload_caddy
	install_autorebuild
	ensure_firewall
	print_report
	log_ok "KCD2 dice solver setup complete."
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
	# Prints 0 to stdout if the URL returns 200 with a non-empty body, else 1.
	# The body-size check matters: a host-matcher misconfiguration answers 200
	# with nothing in it, which a status-only check would call healthy.
	#
	# Certificates are NOT skipped for https URLs — `curl -k` would report an
	# expired or failed-ACME cert as a healthy site, which is precisely the kind
	# of green-while-broken this command exists to catch. The loopback check runs
	# over plain http, so it needs no exception.
	local url="$1" out code size
	out="$(curl -s -o /dev/null -w '%{http_code} %{size_download}' --max-time 10 \
		${2:+-H "Host: $2"} "$url" 2>/dev/null || echo "000 0")"
	read -r code size <<<"$out"
	[[ $code == "200" && ${size:-0} -gt 0 ]] && echo 0 || echo 1
}

status_cmd() {
	print_setup_header "KCD2 dice solver status"

	has_cmd node && status_line 0 "node present" || status_line 1 "node missing"
	has_cmd pnpm && status_line 0 "pnpm present" || status_line 1 "pnpm missing"

	[[ -f "${DICE_SRC}/dist/index.html" ]] &&
		status_line 0 "build present (dist/index.html)" ||
		status_line 1 "build missing — run setup"

	if docker ps --format '{{.Names}}' | grep -qx "$DICE_CONTAINER"; then
		status_line 0 "${DICE_CONTAINER} container running"
		local pid listeners
		pid="$(docker inspect -f '{{.State.Pid}}' "$DICE_CONTAINER" 2>/dev/null || echo "")"
		listeners="$(sudo -n ss -ltnp 2>/dev/null | grep "pid=${pid}," || true)"
		if grep -qE ':(80|443)\b' <<<"$listeners"; then
			status_line 1 "${DICE_CONTAINER} is CONTENDING for :80/:443 with ${CADDY_CONTAINER}"
		else
			status_line 0 "${DICE_CONTAINER} listens only on ${DICE_PORT}"
		fi
	else
		status_line 1 "${DICE_CONTAINER} container not running"
	fi

	status_line "$(check_http "http://127.0.0.1:${DICE_PORT}/" "$DICE_DOMAIN")" \
		"local static server (127.0.0.1:${DICE_PORT}, Host: ${DICE_DOMAIN})"

	[[ -f $DICE_SNIPPET ]] &&
		status_line 0 "Caddy snippet present" ||
		status_line 1 "Caddy snippet missing"

	getent hosts "$DICE_DOMAIN" >/dev/null &&
		status_line 0 "${DICE_DOMAIN} resolves" ||
		status_line 1 "${DICE_DOMAIN} does not resolve"

	status_line "$(check_http "https://${DICE_DOMAIN}/")" \
		"external https://${DICE_DOMAIN}/"

	# The hook lives in .git/hooks, which is not version-controlled, so it is
	# lost on a fresh clone and must be checked rather than assumed. Spelled as
	# an explicit if: with two conditions, A && B || C really would misfire.
	if [[ -x $HOOK_FILE ]] && grep -q "$UNIT_NAME" "$HOOK_FILE" 2>/dev/null; then
		status_line 0 "post-commit auto-rebuild hook installed"
	else
		status_line 1 "post-commit hook missing — re-run setup"
	fi

	[[ -f $UNIT_FILE ]] &&
		status_line 0 "${UNIT_NAME} installed" ||
		status_line 1 "${UNIT_NAME} missing — re-run setup"

	if systemctl --user is-failed --quiet "$UNIT_NAME"; then
		status_line 1 "last auto-rebuild FAILED — journalctl --user -u ${UNIT_NAME}"
	else
		status_line 0 "no failed auto-rebuild recorded"
	fi

	# "not failed" also covers "never ran", so check the artefact rather than the
	# unit: if any source file is newer than the published bundle, the hook is
	# not firing and the site is quietly serving an old build.
	local newest_src
	newest_src="$(find "${DICE_SRC}/src" "${DICE_SRC}/index.html" -type f -newer \
		"${DICE_SRC}/dist/index.html" -print -quit 2>/dev/null || true)"
	if [[ -n $newest_src ]]; then
		status_line 1 "published bundle is STALE (e.g. ${newest_src#"${DICE_SRC}/"}) — run: systemctl --user start ${UNIT_NAME}"
	else
		status_line 0 "published bundle is up to date with src/"
	fi
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

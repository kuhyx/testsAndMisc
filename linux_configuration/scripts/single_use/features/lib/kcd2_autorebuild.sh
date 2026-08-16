#!/bin/bash
# Auto-rebuild timer and unit installation for the dice solver site.
#
# Sourced by setup_kcd2_dice_solver.sh; split out to keep kcd2_expose.sh
# under the 250-line cap. Sourced rather than run, so it inherits the
# caller's strict mode and the variables above the source line.

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
	if [[ -f "${DICE_SRC}/dist/index.html" ]]; then
		status_line 0 "build present (dist/index.html)"
	else
		status_line 1 "build missing — run setup"
	fi
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

	if [[ -f $DICE_SNIPPET ]]; then
		status_line 0 "Caddy snippet present"
	else
		status_line 1 "Caddy snippet missing"
	fi
	if getent hosts "$DICE_DOMAIN" >/dev/null; then
		status_line 0 "${DICE_DOMAIN} resolves"
	else
		status_line 1 "${DICE_DOMAIN} does not resolve"
	fi
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

	if [[ -f $UNIT_FILE ]]; then
		status_line 0 "${UNIT_NAME} installed"
	else
		status_line 1 "${UNIT_NAME} missing — re-run setup"
	fi
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

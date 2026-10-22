#!/bin/bash
#
# redeploy_agent_ready_sites.sh — narrow redeploy + AgentReady check of the
# three public static sites.
#
# Redeploy (skipped with --verify-only), each step independent of the others:
#   - setup_personal_website.sh serve   recreate the kuhy.duckdns.org container
#   - setup_kcd2_dice_solver.sh serve   recreate the dice.kuhy.duckdns.org one
#   - systemctl --user restart signal-bot-popes-site.service
# None of these uses sudo, pacman, a rebuild or the shared edge: build first in
# each site's own repo, then run this to make the new dist/ + Caddyfile live.
#
# Verify: ~/src/utils/agent_ready/check.sh url against each public URL, one
# verdict line per site (PASS, FAIL with the failing check ids, or UNDETERMINED
# when the checker could not reach the site).
#
# Usage:
#   redeploy_agent_ready_sites.sh                 Redeploy, then verify.
#   redeploy_agent_ready_sites.sh --verify-only   Verify only; restarts nothing.
#   redeploy_agent_ready_sites.sh --help          Show this help.
#
# Exit status: 0 when every step and every site passes, 1 otherwise, 2 on a
# usage error.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
readonly CHECKER="${HOME}/src/utils/agent_ready/check.sh"
readonly POPES_UNIT="signal-bot-popes-site.service"
readonly SITES=(
	"https://kuhy.duckdns.org"
	"https://dice.kuhy.duckdns.org"
	"https://popes.kuhy.duckdns.org"
)
# Per-call ceilings keep the whole run inside the 60 s budget even when a site
# hangs; in practice a check takes under a second and a recreate a few.
readonly CHECK_TIMEOUT=10
readonly SERVE_TIMEOUT=20

FAILED=0

usage() {
	grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
	exit "${1:-0}"
}

# run_step <label> <cmd...>: output is shown only when the step fails, so a
# clean run stays at one line per step.
run_step() {
	local label="$1" log rc=0
	shift
	log="$(mktemp)"
	"$@" >"$log" 2>&1 || rc=$?
	if [[ $rc -eq 0 ]]; then
		printf 'redeploy %-28s ok\n' "$label"
	else
		printf 'redeploy %-28s FAILED (exit %d)\n' "$label" "$rc"
		tail -n 15 "$log" | sed 's/^/    /'
		FAILED=1
	fi
	rm -f "$log"
}

redeploy() {
	run_step "personal-website" timeout "$SERVE_TIMEOUT" \
		bash "${SCRIPT_DIR}/setup_personal_website.sh" serve
	run_step "kcd2-dice" timeout "$SERVE_TIMEOUT" \
		bash "${SCRIPT_DIR}/setup_kcd2_dice_solver.sh" serve
	run_step "$POPES_UNIT" systemctl --user restart "$POPES_UNIT"
}

# check_site <url>: one verdict line, sets FAILED on anything but a pass.
check_site() {
	local url="$1" out rc=0 ids
	out="$(timeout "$CHECK_TIMEOUT" "$CHECKER" url "$url" 2>&1)" || rc=$?
	case "$rc" in
	0)
		printf 'PASS          %s\n' "$url"
		return 0
		;;
	3) printf 'UNDETERMINED  %s (checker could not reach it)\n' "$url" ;;
	124) printf 'FAIL          %s (checker timed out after %ss)\n' "$url" "$CHECK_TIMEOUT" ;;
	*)
		ids="$(grep -oE '^FAIL AR-[A-Z]+-[0-9]+' <<<"$out" | cut -d' ' -f2 | sort -u | paste -sd, || true)"
		printf 'FAIL          %s (%s)\n' "$url" "${ids:-exit ${rc}}"
		;;
	esac
	FAILED=1
}

main() {
	local verify_only=0
	case "${1:-}" in
	"") ;;
	--verify-only) verify_only=1 ;;
	-h | --help) usage ;;
	*)
		printf 'Unknown argument: %s\n' "$1" >&2
		usage 2
		;;
	esac
	[[ -x $CHECKER ]] || {
		printf 'AgentReady checker missing: %s\n' "$CHECKER" >&2
		exit 1
	}

	if [[ $verify_only -eq 0 ]]; then
		redeploy
	fi
	local url
	for url in "${SITES[@]}"; do
		check_site "$url"
	done
	return "$FAILED"
}

main "$@"

#!/bin/bash
#
# redeploy_agent_ready_sites.sh — narrow redeploy + AgentReady check of the
# three public static sites.
#
# Redeploy (skipped with --verify-only), the three steps run concurrently:
#   - setup_personal_website.sh serve   recreate the kuhy.duckdns.org container
#   - setup_kcd2_dice_solver.sh serve   recreate the dice.kuhy.duckdns.org one
#   - systemctl --user restart signal-bot-popes-site.service
# None of these uses sudo, pacman, a rebuild or the shared edge: build first in
# each site's own repo, then run this to make the new dist/ + Caddyfile live.
#
# Verify: ~/src/utils/agent_ready/check.sh url against each public URL, all
# three at once, one verdict line per site in a fixed order (PASS, FAIL with
# the failing check ids, or UNDETERMINED when the checker could not reach the
# site or ran out of time).
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
# Timing. A live check takes anywhere from under a second to ~22 s (measured),
# so each one gets the checker's own 45 s network budget, which it enforces
# itself and answers with exit 3 when spent. The whole run must end inside
# 60 s, so that budget is cut to whatever is left before RUN_DEADLINE once the
# redeploy is done. GRACE covers Python start-up and the post-network scoring
# and is also the margin of the outer `timeout`, a backstop for a hung process.
readonly RUN_DEADLINE="${AGENT_READY_RUN_DEADLINE:-55}"
readonly CHECK_BUDGET_MAX=45
readonly CHECK_BUDGET_MIN=3
readonly GRACE=5
readonly SERVE_TIMEOUT=20

FAILED=0
CHECK_BUDGET=0
WORK_DIR=""

usage() {
	# The header block only: it ends at the first non-comment line.
	sed -nE '2,/^[^#]/{/^#( |$)/s/^# ?//p}' "$0"
	exit "${1:-0}"
}

cleanup() {
	[[ -z $WORK_DIR ]] || rm -rf "$WORK_DIR"
}

# in_parallel <fn> <arg>...: run `<fn> <arg>` for every arg at once, then print
# each one's output in argument order. Runs in the background cannot set
# FAILED themselves, so their exit status is collected here.
in_parallel() {
	local fn="$1" arg i=0 pids=()
	shift
	for arg in "$@"; do
		"$fn" "$arg" >"${WORK_DIR}/${i}.out" 2>&1 &
		pids+=("$!")
		i=$((i + 1))
	done
	for i in "${!pids[@]}"; do
		wait "${pids[$i]}" || FAILED=1
		cat "${WORK_DIR}/${i}.out"
	done
}

# run_step <label> <cmd...>: output is shown only when the step fails, so a
# clean run stays at one line per step.
run_step() {
	local label="$1" out rc=0
	shift
	out="$("$@" 2>&1)" || rc=$?
	if [[ $rc -eq 0 ]]; then
		printf 'redeploy %-28s ok\n' "$label"
	else
		printf 'redeploy %-28s FAILED (exit %d)\n' "$label" "$rc"
		tail -n 15 <<<"$out" | sed 's/^/    /'
	fi
	return "$rc"
}

redeploy_step() {
	case "$1" in
	personal-website)
		run_step "$1" timeout "$SERVE_TIMEOUT" bash "${SCRIPT_DIR}/setup_personal_website.sh" serve
		;;
	kcd2-dice)
		run_step "$1" timeout "$SERVE_TIMEOUT" bash "${SCRIPT_DIR}/setup_kcd2_dice_solver.sh" serve
		;;
	*) run_step "$1" timeout "$SERVE_TIMEOUT" systemctl --user restart "$1" ;;
	esac
}

# check_site <url>: one verdict line; non-zero on anything but a pass.
check_site() {
	local url="$1" out rc=0 ids
	out="$(timeout "$((CHECK_BUDGET + GRACE))" "$CHECKER" url "$url" --budget "$CHECK_BUDGET" 2>&1)" || rc=$?
	case "$rc" in
	0)
		printf 'PASS          %s\n' "$url"
		return 0
		;;
	3) printf 'UNDETERMINED  %s (checker could not reach it within %ss)\n' "$url" "$CHECK_BUDGET" ;;
	124) printf 'FAIL          %s (checker hung past %ss)\n' "$url" "$((CHECK_BUDGET + GRACE))" ;;
	*)
		ids="$(grep -oE '^FAIL AR-[A-Z]+-[0-9]+' <<<"$out" | cut -d' ' -f2 | sort -u | paste -sd, || true)"
		printf 'FAIL          %s (%s)\n' "$url" "${ids:-exit ${rc}}"
		;;
	esac
	return 1
}

verify() {
	local url
	CHECK_BUDGET=$((RUN_DEADLINE - SECONDS - GRACE))
	if [[ $CHECK_BUDGET -gt $CHECK_BUDGET_MAX ]]; then
		CHECK_BUDGET=$CHECK_BUDGET_MAX
	fi
	if [[ $CHECK_BUDGET -lt $CHECK_BUDGET_MIN ]]; then
		for url in "${SITES[@]}"; do
			printf 'UNDETERMINED  %s (no time left before the %ss deadline)\n' "$url" "$RUN_DEADLINE"
		done
		FAILED=1
		return 0
	fi
	in_parallel check_site "${SITES[@]}"
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
	WORK_DIR="$(mktemp -d)"
	trap cleanup EXIT

	if [[ $verify_only -eq 0 ]]; then
		in_parallel redeploy_step personal-website kcd2-dice "$POPES_UNIT"
	fi
	verify
	return "$FAILED"
}

main "$@"

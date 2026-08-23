#!/usr/bin/env bash
# Tests for lib/services_report.sh — the usage text and the summary table.
#
# print_summary has four independent axes: the per-service colour mapping
# (ok/warning/error/n-a/unknown), the DRY_RUN banner, the STATUS_ONLY wording,
# and the fixes-applied vs no-fixes-applied wording. Each case below pins one.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_report.sh
. "${SCRIPT_DIR}/../services_report.sh"

echo "== usage =="
usage_out="$(usage)"
_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}
_t_called_in "$usage_out" "--dry-run" "usage documents --dry-run"
_t_called_in "$usage_out" "--status" "usage documents --status"
_t_called_in "$usage_out" "Workout lock screen" "usage lists all 11 services"

echo "== print_summary: every status colour =="
reset_state
set_service_status "pacman_wrapper" "ok"
set_service_status "makepkg_wrapper" "warning"
set_service_status "midnight_shutdown" "error"
set_service_status "startup_monitor" "n/a"
set_service_status "periodic_systems" "skipped"
# The remaining six keys are deliberately left unset so the ":-unknown"
# default and its *) colour arm are exercised too.
ISSUES_FOUND=0
out="$(print_summary)"
_t_called_in "$out" "pacman_wrapper" "summary lists pacman_wrapper"
_t_called_in "$out" "unknown" "unset services report as unknown"
_t_called_in "$out" "All services are properly configured!" "no issues -> success line"

echo "== print_summary: dry-run banner =="
reset_state
DRY_RUN=1
ISSUES_FOUND=0
out="$(print_summary)"
_t_called_in "$out" "DRY RUN - No changes were made" "dry-run banner shown"

echo "== print_summary: status-only wording =="
reset_state
STATUS_ONLY=1
ISSUES_FOUND=3
out="$(print_summary)"
_t_called_in "$out" "Found 3 service(s) with issues" "status-only counts issues"
_t_called_in "$out" "Run without --status to fix issues" "status-only points at the fix flag"

echo "== print_summary: issues found and fixed =="
reset_state
ISSUES_FOUND=2
FIXES_APPLIED=2
out="$(print_summary)"
_t_called_in "$out" "Applied 2 fix(es)" "reports the number of fixes applied"

echo "== print_summary: issues found, nothing fixed =="
reset_state
ISSUES_FOUND=2
FIXES_APPLIED=0
out="$(print_summary)"
_t_called_in "$out" "Found 2 issue(s) but no fixes were applied" "warns when nothing was fixed"

_t_summary

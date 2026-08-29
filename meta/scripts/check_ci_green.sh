#!/bin/bash

# ============================================================================
# Refuse to build on a known-broken baseline.
#
# Checks the most recent completed GitHub Actions run for each required
# workflow on main. A definitively RED baseline blocks the commit; anything
# this cannot determine (offline, no gh, not authenticated, no runs yet) warns
# and passes.
#
# Why fail open on "unknown": this runs on EVERY commit. The real guarantee
# that a change does not break CI is the pre-push ci-mirror hook, which runs
# the workflows' local equivalent against the actual diff. This hook is only
# the broken-baseline net, and making every commit depend on network
# reachability would cost far more than it catches.
#
# Why fail closed on "red": committing more work onto a main that is already
# failing is how a red baseline gets buried under changes that make it harder
# to bisect.
#
# Bypass for a deliberate fix-forward commit. It must be given TWICE, because
# this hook runs at both stages: once at commit, and again inside the pre-push
# CI mirror's clean-worktree `pre-commit` run, which sees the same still-red
# baseline. The variable is read from the environment and the mirror does not
# scrub it, so exporting it for the push carries through:
#   CI_GREEN_SKIP=1 git commit ...
#   CI_GREEN_SKIP=1 git push
# ============================================================================

set -euo pipefail

readonly SCRIPT_NAME="${0##*/}"
# Workflows that must be green. python-tests.yml is deliberately absent: it is
# path-filtered, so a shell-only commit never triggers it and its "latest run"
# can legitimately be an old one.
readonly REQUIRED_WORKFLOWS=("Pre-commit checks" "Shell tests")
readonly TIMEOUT_SECONDS=5

warn_and_pass() {
	printf '%s: %s\n' "$SCRIPT_NAME" "$1" >&2
	printf '%s: skipping the CI-baseline check (pre-push ci-mirror is the real gate).\n' \
		"$SCRIPT_NAME" >&2
	exit 0
}

if [[ -n ${CI_GREEN_SKIP:-} ]]; then
	warn_and_pass "CI_GREEN_SKIP is set"
fi

# Inside CI itself there is no useful "previous run on main" to consult, and
# the runner may not have a token with the right scope.
if [[ -n ${GITHUB_ACTIONS:-} ]]; then
	warn_and_pass "running inside GitHub Actions"
fi

if ! command -v gh >/dev/null 2>&1; then
	warn_and_pass "gh is not installed"
fi

if ! timeout "$TIMEOUT_SECONDS" gh auth status >/dev/null 2>&1; then
	warn_and_pass "gh is not authenticated or GitHub is unreachable"
fi

failed=()
for workflow in "${REQUIRED_WORKFLOWS[@]}"; do
	# --status completed so an in-progress run does not read as a failure; the
	# question is whether the last SETTLED run was red.
	conclusion="$(timeout "$TIMEOUT_SECONDS" gh run list \
		--workflow "$workflow" --branch main --status completed \
		--limit 1 --json conclusion --jq '.[0].conclusion // empty' 2>/dev/null || true)"

	case "$conclusion" in
	success | "") : ;; # green, or no settled run to judge
	*) failed+=("$workflow ($conclusion)") ;;
	esac
done

if [[ ${#failed[@]} -gt 0 ]]; then
	printf '%s: main is RED on GitHub Actions:\n' "$SCRIPT_NAME" >&2
	printf '  - %s\n' "${failed[@]}" >&2
	printf '\nCommitting more work onto a failing baseline buries the breakage.\n' >&2
	printf 'Fix it first, or if THIS commit is the fix:\n' >&2
	printf '  CI_GREEN_SKIP=1 git commit ...\n' >&2
	printf '  CI_GREEN_SKIP=1 git push\n' >&2
	printf '(both: the pre-push CI mirror re-runs this same check.)\n' >&2
	exit 1
fi

exit 0

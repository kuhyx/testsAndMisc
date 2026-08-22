#!/usr/bin/env bash

# ============================================================================
# The coverage bar for check_shell_coverage.sh.
#
# Split out of that script on 2026-08-22 to keep both files under the repo's
# 250-line cap. Sourced, not executed.
# ============================================================================

# A lib is covered when its directory has a suite AND that suite drives the
# lib to COVERAGE_BAR% line coverage.
#
# This was a presence check until 2026-08-22 -- "a run_all.sh exists beside
# it" -- which is satisfiable by an empty suite that sources the lib and
# asserts nothing. The bar is a measured percentage because that is the only
# version a suite cannot trivially pass.
#
# 100% is reachable without suppressions and without touching production
# source: run the suite inside the user+mount namespace of
# shell_coverage_jail.sh and the sudo-writes, systemd units and nftables rules
# execute for real against a throwaway /etc. Measured on the repo's hardest
# library, dot_resolver_install.sh (15 root ops, 5 system writes): 39/39.
readonly COVERAGE_BAR=100

is_covered() {
	local path="$1"
	local suite
	suite="$(dirname "$path")/tests/run_all.sh"
	[[ -f "$suite" ]] || return 1

	# Presence alone is enough when the measurement cannot be made: kcov is a
	# developer dependency, and a hook that hard-fails on a missing tool would
	# block commits on any machine without it. The CI job carries the tool and
	# enforces the number, so nothing merges on presence alone.
	command -v kcov >/dev/null 2>&1 || return 0
	command -v unshare >/dev/null 2>&1 || return 0

	"$REPO_ROOT/meta/scripts/shell_coverage_jail.sh" \
		--subject "$suite" \
		--bind /etc --bind /usr/local/bin --bind /var/lib \
		--measure "$(basename "$path")" \
		--min "$COVERAGE_BAR" \
		-- "" >/dev/null 2>&1
}

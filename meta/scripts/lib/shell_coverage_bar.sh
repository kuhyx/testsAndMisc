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

	# A suite declares the mounts and seeds it needs in a `jail_args` file
	# beside its run_all.sh -- the same marker ci_mirror.sh and
	# shell-tests.yml read. Hardcoding flags here was a latent gate failure:
	# the features/lib suite needs /usr/local/share and /etc/pki, and without
	# them it ABORTS partway under `set -e`. The coverage number still printed
	# (kcov had already recorded the lines the dead run reached), so the gate
	# would have passed a lib whose suite never finished.
	local jail_args=()
	local args_file
	args_file="$(dirname "$suite")/jail_args"
	if [[ -f "$args_file" ]]; then
		local arg
		while IFS= read -r arg; do
			jail_args+=("$arg")
		done < <(grep -v '^#\|^$' "$args_file" || true)
		if [[ ${#jail_args[@]} -eq 0 ]]; then
			echo "Error: jail_args is present but empty: $args_file" >&2
			return 1
		fi
	else
		# No marker: the suite runs without needing anything mounted, so give
		# it the historical defaults rather than nothing.
		jail_args=(--bind /etc --bind /usr/local/bin --bind /var/lib)
	fi

	# --fail-on-case-error: a suite that dies partway must fail the gate, not
	# be graded on however many lines it managed to reach first.
	"$REPO_ROOT/meta/scripts/shell_coverage_jail.sh" \
		--subject "$suite" \
		"${jail_args[@]}" \
		--measure "$(basename "$path")" \
		--min "$COVERAGE_BAR" \
		--fail-on-case-error \
		-- "" >/dev/null 2>&1
}

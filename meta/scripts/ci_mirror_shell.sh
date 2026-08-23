# shellcheck shell=bash
# ============================================================================
# ci_mirror_shell.sh — the shell half of the CI mirror.
#
# Sourced by ci_mirror.sh. Splits out of it to stay under the 250-line cap.
# Provides run_shell_test_gate, which mirrors the shell-tests workflow, and
# run_jailed_suite, which wraps a suite that declares a jail_args file.
#
# Uses ci_mirror.sh's CHECKOUT/fail/log and ci_mirror_range.sh's
# select_shell_suites / needs_full_sweep.
# ============================================================================

# Mirror the shell-tests workflow's side-effect-free half.
#
# Without this, ci-mirror covered the pre-commit and python-tests workflows but
# not Shell tests, so a shell change could pass every local gate and still go
# red on push — which is exactly what happened repeatedly during the
# 250-line-cap campaign: three separate test files asserted on code that a
# split had moved, and each was only caught after the push.
#
# The Arch-container half of that workflow is deliberately NOT mirrored: it
# needs an Arch userland running as root to touch /etc, which is what the
# disposable container provides and a developer machine must not.
# A suite that writes to real system paths declares it with a `jail_args` file
# beside its run_all.sh, holding the --bind/--seed-* flags it needs. Such a
# suite REFUSES to run bare -- that guard is what stops a test run from
# rewriting the developer's own /etc -- so invoking it directly fails the gate.
#
# Fails closed: a marker present but empty is a mistake, not a licence to skip.
run_jailed_suite() {
	local runner="$1"
	local args_file="$CHECKOUT/${runner%/run_all.sh}/jail_args"

	local jail_args=()
	while IFS= read -r arg; do
		jail_args+=("$arg")
	done < <(grep -v '^#\|^$' "$args_file" || true)

	if [[ ${#jail_args[@]} -eq 0 ]]; then
		fail "jail_args is present but empty: $args_file"
	fi

	# --min 0: this gate asks "did the assertions pass?", not "is the lib at
	# 100%?". Without it the jail measures the runner itself against its
	# default --min 100 and fails the push on a number no one asked for.
	# The coverage bar is check_shell_coverage.sh's job, per-lib and --measure'd.
	# Output is captured, not discarded: on success it is noise, but on failure
	# it holds the `warn: case exited` line and the suite's own FAIL: lines.
	# Without this the gate reports only "suite failed" and cannot be diagnosed.
	local out
	if ! out="$(cd "$CHECKOUT" && bash meta/scripts/shell_coverage_jail.sh \
		--subject "$runner" "${jail_args[@]}" \
		--min 0 --fail-on-case-error -- "" 2>&1)"; then
		printf '%s\n' "$out" >&2
		fail "jailed lib/tests suite failed: $runner"
	fi
}

run_shell_test_gate() {
	local paths="$1"
	local all_runners
	all_runners="$(cd "$CHECKOUT" && find . -path ./node_modules -prune -o \
		-path '*/lib/tests/run_all.sh' -print | sort)"

	if [[ -z "$all_runners" ]]; then
		fail "no lib/tests/run_all.sh found — the discovery glob is wrong"
	fi

	local selected
	if needs_full_sweep "$paths"; then
		selected="$all_runners"
	else
		selected="$(select_shell_suites "$paths" "$all_runners")"
	fi

	if [[ -z "$selected" ]]; then
		log "no shell files in the push range — skipping the lib/tests suites"
	else
		log "lib/tests suites (mirrors the shell-tests workflow)"
	fi

	local runners=()
	while IFS= read -r runner; do
		[[ -n "$runner" ]] && runners+=("$runner")
	done <<<"$selected"

	local runner
	for runner in "${runners[@]}"; do
		if [[ -f "$CHECKOUT/${runner%/run_all.sh}/jail_args" ]]; then
			run_jailed_suite "$runner"
		else
			(cd "$CHECKOUT" && "$runner" >/dev/null) ||
				fail "lib/tests suite failed: $runner"
		fi
	done

	log "side-effect-free shell tests (mirrors the shell-tests workflow)"
	# Parsed OUT of the workflow rather than duplicated here. A hardcoded copy
	# drifts the moment someone adds a test to the workflow, and a mirror that
	# silently checks less than CI is worse than no mirror: it reports safe.
	# The awk range is the shell-tests job's `tests=( ... )` array, taking the
	# first one only — the second belongs to the Arch container job, which is
	# deliberately not mirrored.
	local shell_tests=()
	while IFS= read -r shell_test; do
		shell_tests+=("$shell_test")
	done < <(awk '/^ *tests=\(/{n++} n==1 && /^ *test_.*\.sh *$/{gsub(/ /,"");print} n==1 && /^ *\)/{exit}' \
		"$CHECKOUT/.github/workflows/shell-tests.yml")

	if [[ ${#shell_tests[@]} -eq 0 ]]; then
		fail "could not parse the test list out of shell-tests.yml"
	fi

	local shell_test
	for shell_test in "${shell_tests[@]}"; do
		(cd "$CHECKOUT" && bash "linux_configuration/tests/$shell_test" >/dev/null 2>&1) ||
			fail "shell test failed: $shell_test"
	done
}

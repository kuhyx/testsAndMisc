#!/usr/bin/env bash
# lib/tests/run_all.sh — run every transcribe lib test in one process tree.
#
# Also the subject handed to shell_coverage_jail.sh when measuring coverage of
# a lib in this directory: coverage is only complete across the whole suite.
#
# No jail_args file sits beside this runner, and that is deliberate: these
# suites intercept every package manager and sudo call with a PATH stub dir,
# so they touch nothing outside their own mktemp -d. Both ci_mirror.sh and
# the shell-tests workflow therefore run this runner directly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

failed=0
for test_script in "${SCRIPT_DIR}"/test_*.sh; do
	printf '\n### %s\n' "$(basename "$test_script")"
	if ! "$test_script"; then
		failed=$((failed + 1))
	fi
done

if [[ $failed -gt 0 ]]; then
	printf '\n%d test file(s) FAILED\n' "$failed"
	exit 1
fi

printf '\nAll transcribe lib test files passed.\n'

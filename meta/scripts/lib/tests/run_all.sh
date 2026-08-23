#!/usr/bin/env bash
# lib/tests/run_all.sh — run every shell-coverage tooling test in one go, and
# exit non-zero if any of them fails.
#
# These three libs build and measure the coverage jail, so they are the one
# corner of the repo the jail cannot check itself. The tests are pure: they
# call the file-writing functions against a temp $JAIL and assert on what was
# written. Nothing here mounts, unshares, or runs kcov.
set -uo pipefail

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

printf '\nAll shell-coverage tooling test files passed.\n'

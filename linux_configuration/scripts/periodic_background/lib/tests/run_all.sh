#!/usr/bin/env bash
# lib/tests/run_all.sh — run every check_and_enable_services test in one
# process tree, and exit non-zero if any of them fails.
#
# This exists for two reasons. It is the single command CI and a human can run;
# and it is the subject handed to shell_coverage.sh, because coverage of a lib
# is only complete across the whole suite. services_common.sh, for instance, is
# covered jointly by test_services_common.sh and test_services_report_and_fix.sh
# -- the two were split apart to satisfy the 250-line cap, not because either
# is a complete test of the lib, so measuring either alone under-reports.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

failed=0
for test_script in "${SCRIPT_DIR}"/test_services_*.sh; do
	printf '\n### %s\n' "$(basename "$test_script")"
	if ! "$test_script"; then
		failed=$((failed + 1))
	fi
done

if [[ $failed -gt 0 ]]; then
	printf '\n%d test file(s) FAILED\n' "$failed"
	exit 1
fi

printf '\nAll check_and_enable_services test files passed.\n'

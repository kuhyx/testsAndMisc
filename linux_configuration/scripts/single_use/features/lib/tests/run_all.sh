#!/usr/bin/env bash
# lib/tests/run_all.sh — run every features/lib test in one process tree.
#
# Also the subject handed to shell_coverage_jail.sh: coverage of a lib is only
# complete across the whole suite.
#
# These suites execute their subjects FOR REAL, including sudo-writes to
# /etc/systemd/system and nftables rules. They must therefore run inside the
# namespace jail; see the header of test_dot_resolver_install.sh.
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

printf '\nAll features/lib test files passed.\n'

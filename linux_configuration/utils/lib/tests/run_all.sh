#!/usr/bin/env bash
# lib/tests/run_all.sh — run every generate_study_materials test in one process
# tree, and exit non-zero if any of them fails.
#
# Also the subject handed to shell_coverage.sh: coverage of a lib is only
# complete across the whole suite, since the doc-URL builders are exercised both
# directly and through get_doc_url's dispatch.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

failed=0
for test_script in "${SCRIPT_DIR}"/test_study_*.sh; do
	printf '\n### %s\n' "$(basename "$test_script")"
	if ! "$test_script"; then
		failed=$((failed + 1))
	fi
done

if [[ $failed -gt 0 ]]; then
	printf '\n%d test file(s) FAILED\n' "$failed"
	exit 1
fi

printf '\nAll generate_study_materials test files passed.\n'

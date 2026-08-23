#!/usr/bin/env bash
# Runs every linux_configuration/scripts/lib test.
#
# The glob is test_*.sh, NOT one prefix per subject: a prefix glob silently
# skips every suite added after it — including in the CI discovery step in
# shell-tests.yml, which runs this file. Only common_datetime is left here
# since the mtk_* libraries moved to github.com/kuhyx/mtk-root, but the glob
# stays generic for the same reason it was generic before.
#
# This file's existence is what meta/scripts/check_shell_coverage.sh checks:
# is_covered() tests for tests/run_all.sh and nothing more, so an empty one
# here would mark every library in the parent directory covered while testing
# nothing. The suites it runs, and the gaps they leave, are named in
# mtk_harness.sh's header.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rc=0
for t in "$HERE"/test_*.sh; do
	printf '\n=== %s ===\n' "$(basename "$t")"
	# Each suite exits non-zero on failure; keep going so one red suite does not
	# hide the state of the others, then fail the run as a whole.
	# Invoked directly, NOT as `bash "$t"`: under kcov the latter instruments
	# bash itself and reports zero lines for every lib. A fresh process per
	# suite also matters here: a library that declares readonly values aborts
	# under set -e if it is sourced twice in one shell.
	"$t" || rc=1
done

exit "$rc"

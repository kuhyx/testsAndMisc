#!/usr/bin/env bash
# Runs the suite that covers this directory's libraries.
#
# The libraries here are sourced by ../../boot-repair and depend on its strict
# mode, its $ROOT/$MODE globals and its output helpers, so they cannot be
# exercised in isolation without reimplementing all of that. The real suite
# drives the entry script against throwaway fixture root trees, which executes
# every one of them end to end -- that is the honest test, so this runner
# delegates to it rather than standing up a second, weaker harness.
#
# This file's existence is also what meta/scripts/check_shell_coverage.sh
# checks: is_covered() looks for tests/run_all.sh beside the libs and nothing
# more, so a stub here would mark them covered while testing nothing.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SUITE="${HERE}/../../tests/test_boot_repair.sh"

[[ -x "$SUITE" ]] || {
	printf 'boot_recovery lib tests: %s is missing or not executable\n' "$SUITE" >&2
	exit 1
}

printf '\n=== %s ===\n' "$(basename "$SUITE")"
exec "$SUITE"

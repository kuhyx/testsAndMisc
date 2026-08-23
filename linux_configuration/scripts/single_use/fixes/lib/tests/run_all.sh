#!/usr/bin/env bash
# lib/tests/run_all.sh — run every fixes lib test in one process tree.
#
# Also the subject handed to shell_coverage_jail.sh when measuring coverage of
# a lib in this directory: coverage of a lib is only complete across the whole
# suite, and is_covered() builds exactly this subject. Never measure a single
# test file -- the runner's number is the one that counts, and it can be lower
# than a suite's own.
#
# No jail_args file sits beside this runner, and that is deliberate: the
# harness confines every write to its own `mktemp -d` and intercepts each
# external command with a PATH stub dir, so these suites touch nothing outside
# it. Both ci_mirror.sh and the shell-tests workflow therefore run this runner
# directly rather than wrapping it in the namespace jail.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# One _t_hide shim farm for the whole run. Each test file gets its own
# $TEST_TMPDIR, so without this the farm -- a symlink per executable on PATH,
# ~13.5k of them and ~4.6s to build -- was rebuilt once per distinct tool set,
# roughly sixteen times a run. Its contents depend only on the tool list and
# the original PATH, so sharing it across files changes nothing but the clock.
LIB_TEST_HIDE_CACHE="$(mktemp -d)"
export LIB_TEST_HIDE_CACHE
trap 'rm -rf "${LIB_TEST_HIDE_CACHE}"' EXIT

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

printf '\nAll fixes lib test files passed.\n'

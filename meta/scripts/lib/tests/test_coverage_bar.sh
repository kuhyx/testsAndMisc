#!/usr/bin/env bash
# is_covered: the shell-coverage ratchet's predicate.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./coverage_tool_harness.sh
. "$HERE/coverage_tool_harness.sh"
# shellcheck source=../shell_coverage_bar.sh
. "$HERE/../shell_coverage_bar.sh"

tmp="$(mktemp -d -t covbar-XXXXXX)"
trap 'rm -rf "$tmp"' EXIT

# A lib whose directory has no tests/ at all.
mkdir -p "$tmp/nosuite/lib"
: >"$tmp/nosuite/lib/thing.sh"
if is_covered "$tmp/nosuite/lib/thing.sh"; then
	_t_fail "a lib with no tests/ dir is uncovered"
else
	_t_pass "a lib with no tests/ dir is uncovered"
fi

# A tests/ directory that exists but has no run_all.sh: still uncovered. The
# suite is identified by its runner, not by the directory.
mkdir -p "$tmp/emptytests/lib/tests"
: >"$tmp/emptytests/lib/thing.sh"
: >"$tmp/emptytests/lib/tests/test_thing.sh"
if is_covered "$tmp/emptytests/lib/thing.sh"; then
	_t_fail "a tests/ dir without run_all.sh is uncovered"
else
	_t_pass "a tests/ dir without run_all.sh is uncovered"
fi

# The covered case.
mkdir -p "$tmp/good/lib/tests"
: >"$tmp/good/lib/thing.sh"
: >"$tmp/good/lib/tests/run_all.sh"
if is_covered "$tmp/good/lib/thing.sh"; then
	_t_pass "a lib beside a tests/run_all.sh is covered"
else
	_t_fail "a lib beside a tests/run_all.sh is covered"
fi

# The runner is looked up beside the LIB, not anywhere up the tree: a suite one
# directory up must not cover a nested lib.
mkdir -p "$tmp/nested/lib/tests" "$tmp/nested/lib/inner"
: >"$tmp/nested/lib/tests/run_all.sh"
: >"$tmp/nested/lib/inner/thing.sh"
if is_covered "$tmp/nested/lib/inner/thing.sh"; then
	_t_fail "a suite one level up does not cover a nested lib"
else
	_t_pass "a suite one level up does not cover a nested lib"
fi

# A run_all.sh that is a DIRECTORY is not a runner.
mkdir -p "$tmp/dirrunner/lib/tests/run_all.sh"
: >"$tmp/dirrunner/lib/thing.sh"
if is_covered "$tmp/dirrunner/lib/thing.sh"; then
	_t_fail "a directory named run_all.sh is not a suite"
else
	_t_pass "a directory named run_all.sh is not a suite"
fi

_t_summary

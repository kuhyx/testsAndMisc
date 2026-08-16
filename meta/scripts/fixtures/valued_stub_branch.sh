#!/usr/bin/env bash

# Regression fixture: the silent-stub trap.
#
# `du` stubbed to print NOTHING makes size="" , so `((size > 0))` is false,
# the guarded branch is skipped, and two traces match perfectly while
# exercising none of the code under test.
#
#   trace_shell_split.sh valued_stub_branch.sh --stub du
#     -> size=[] / branch skipped, never reaches the guarded sudo rm -rf
#   trace_shell_split.sh valued_stub_branch.sh --stub 'du=4096'
#     -> size=[4096] / BRANCH TAKEN, and the sudo call is captured
#
# The point of keeping this: an empty stub is not a passing test, it is a test
# that never ran.

set -euo pipefail

size="$(du -sk /some/dir 2>/dev/null | cut -f1)"
echo "size=[$size]"

if ((${size:-0} > 0)); then
	echo "BRANCH TAKEN"
	sudo rm -rf /some/dir/cache
else
	echo "branch skipped"
fi

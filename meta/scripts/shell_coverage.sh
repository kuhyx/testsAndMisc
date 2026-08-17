#!/usr/bin/env bash

# ============================================================================
# Measure line coverage of a shell library from its test script, via kcov.
#
#   shell_coverage.sh <test-script> <subject-basename> [min-percent]
#
# Reports covered/total and the uncovered line numbers, and exits 1 when the
# result is below min-percent (default 100).
#
# Two things about kcov that cost an hour to find, both worth keeping:
#
#   1. It must be given the test script DIRECTLY, not `bash <script>`. Handed
#      `bash foo.sh` it instruments the bash binary, finds no shell source,
#      and reports 0/0 at 0.00% -- which reads exactly like "nothing is
#      covered" rather than "nothing was measured".
#   2. Per-line detail is only in cov.xml. The summary coverage.json carries
#      just the percentage, so it cannot tell you WHICH lines are missing.
#
# It does follow into subprocesses, so a harness that stages the subject into
# a temp dir and runs each case as a child still gets measured -- which is why
# --include-pattern matches on basename rather than an absolute path.
# ============================================================================

set -euo pipefail

readonly SCRIPT_NAME="${0##*/}"

usage() {
    echo "Usage: $SCRIPT_NAME <test-script> <subject-basename> [min-percent]"
    echo
    echo "  test-script       the test to run, e.g. phone_focus_mode/lib/tests/test_x.sh"
    echo "  subject-basename  the file to measure, e.g. dns_iptables.sh"
    echo "  min-percent       fail below this (default 100)"
    exit 0
}

[[ $# -ge 1 && ( "$1" == "-h" || "$1" == "--help" ) ]] && usage

if [[ $# -lt 2 ]]; then
    echo "Error: need a test script and a subject basename" >&2
    exit 1
fi

readonly TEST_SCRIPT="$1"
readonly SUBJECT="$2"
readonly MIN_PERCENT="${3:-100}"

if ! command -v kcov >/dev/null 2>&1; then
    echo "Error: kcov is not installed (pacman -S kcov)" >&2
    exit 1
fi

if [[ ! -f "$TEST_SCRIPT" ]]; then
    echo "Error: no such test script: $TEST_SCRIPT" >&2
    exit 1
fi

OUT_DIR="$(mktemp -d)"
readonly OUT_DIR
cleanup() { rm -rf "$OUT_DIR"; }
trap cleanup EXIT

# Direct invocation, per note 1 above.
if ! kcov --include-pattern="$SUBJECT" "$OUT_DIR" "$TEST_SCRIPT" >"$OUT_DIR/run.log" 2>&1; then
    echo "Error: the test script failed under kcov; its output follows" >&2
    tail -20 "$OUT_DIR/run.log" >&2
    exit 1
fi

python3 "$(dirname "$0")/shell_coverage_report.py" "$OUT_DIR" "$SUBJECT" "$MIN_PERCENT"

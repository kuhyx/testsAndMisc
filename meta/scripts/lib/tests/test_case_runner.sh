#!/usr/bin/env bash
# write_case_runner: the script that executes cases INSIDE the jail.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./coverage_tool_harness.sh
. "$HERE/coverage_tool_harness.sh"
# shellcheck source=../shell_coverage_case_runner.sh
. "$HERE/../shell_coverage_case_runner.sh"

_t_new_jail
write_case_runner
runner="$JAIL/run_cases.sh"

_t_eq "yes" "$([[ -x "$runner" ]] && echo yes)" "the runner is written executable"
body="$(cat "$runner")"

# It runs in the child namespace, so it must be syntactically valid on its own.
bash -n "$runner" 2>/dev/null
_t_eq "0" "$?" "the emitted runner parses as bash"

# Both passes must be present, and they cannot be merged: kcov's ptrace and
# xtrace destroy each other's numbers.
_t_has "$body" "kcov --include-pattern" "the kcov pass invokes kcov with an include pattern"
_t_has "$body" "BASH_ENV=" "the trace pass delivers tracing via BASH_ENV"
_t_lacks "$body" "SHELLOPTS=xtrace" "tracing is NOT delivered via SHELLOPTS (readonly, and dropped when privileged)"

# fd 199, deliberately high: a subject doing `exec 9>...` would clobber a low fd
# and silently truncate the trace.
_t_has "$body" "BASH_XTRACEFD=199" "the trace uses the high fd 199"
_t_has "$body" '199>>' "and the runner opens 199 itself so the subject cannot swallow it"

# Every case is bounded and has stdin closed: a subject that reads stdin
# otherwise blocks on the caller's terminal for the whole timeout.
_t_has "$body" "timeout --kill-after=10s" "each case runs under a bounded timeout"
_t_has "$body" "</dev/null" "each case has stdin closed"

# A timed-out or failing case must be RECORDED, not swallowed: swallowing it is
# what let a deliberately-broken assertion exit 0 through the push gate.
_t_has "$body" "case timed out" "a timeout is reported"
_t_has "$body" "case exited" "a non-zero case is reported"
_t_has "$body" "case_failures" "and both are recorded to a case_failures file"
_t_has "$body" "124" "SIGTERM-timeout (124) is treated as a timeout"
_t_has "$body" "137" "SIGKILL-timeout (137) is treated as a timeout too"

# PATH is pinned to the jail's shim dir FIRST, so a shimmed tool wins over the
# host's real one.
_t_has "$body" "PATH=\"${DOLLAR}jail/bin:" "the jail's bin/ is first on PATH"

# The heredoc is quoted, so the runner's own variables survive to the child
# shell rather than being expanded when the file is written.
_t_has "$body" "${DOLLAR}1" "the runner reads its arguments at run time"
_t_lacks "$body" "$JAIL" "the writing shell's JAIL path is not baked in"

_t_drop_jail
_t_summary

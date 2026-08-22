#!/usr/bin/env bash

# ============================================================================
# write_case_runner — emit the script that executes the cases INSIDE the jail.
#
# Split out of shell_coverage_jail.sh to hold that file under the 250-line cap
# after --fail-on-case-error was added. Sourced, never run: it needs $JAIL from
# its caller.
#
# The runner is written to a file rather than inlined into the `unshare`
# command because it executes in the child namespace: a quoted inline block
# would have to defer every expansion to the child shell, which reads as a
# quoting bug and trips SC2016.
#
# TWO PASSES, and they cannot be merged. kcov instruments via ptrace; bash's
# xtrace is a shell feature. Running both over one process was measured to
# destroy kcov's numerator outright -- with SHELLOPTS=xtrace set, every line
# kcov had recorded as hits="1" comes back hits="0". So:
#
#   pass "kcov"  -> the instrumentable LINE SET (the denominator) plus kcov's
#                   own hit counts, which are correct for some lines and
#                   missing for others (defect (b) in docs/kcov-under-report.md).
#   pass "trace" -> the EXECUTED line set, from a PS4 xtrace. This is the
#                   authoritative numerator; kcov's hits are unioned in so a
#                   line either instrument saw counts as covered.
#
# Tracing is delivered via BASH_ENV, not SHELLOPTS/PS4, and the reason is
# measured, not stylistic. Three findings, each of which yields a silently
# WRONG trace rather than an error:
#
#   1. `set -x` does NOT reach child bash processes, and the suites drive
#      their subjects several processes deep.
#   2. SHELLOPTS is a READONLY variable inside bash, so `export
#      SHELLOPTS=xtrace` fails with "readonly variable" and tracing never
#      turns on. It only works placed in the environment OF the process.
#   3. Decisive: bash started under `unshare --user --map-root-user` runs in
#      PRIVILEGED mode (uid != euid) and DISCARDS an inherited PS4, falling
#      back to the default "+ " -- while still honouring SHELLOPTS=xtrace.
#      The trace then carries no file:line prefix at all and every subject
#      reads as 0% covered.
#
# BASH_ENV survives all three: every non-interactive bash sources it at
# startup, so PS4 is ASSIGNED from inside the shell (where privileged mode
# cannot strip it) and `set -x` is re-applied per process, including children.
#
# BASH_XTRACEFD uses fd 199, not a low fd: subjects and harnesses open their
# own descriptors, and a subject doing `exec 9>...` would silently clobber the
# trace mid-run and truncate it.
# ============================================================================

write_case_runner() {
	# The runner below executes INSIDE the namespace, so it is written out as
	# its own file rather than inlined: a quoted inline block would have to
	# defer every expansion to the child shell, which reads as a quoting bug
	# and trips SC2016.
	cat >"$JAIL/run_cases.sh" <<'INNER'
#!/usr/bin/env bash
set -u
jail="$1"
subject_dir="$2"
subject_base="$3"
measure_base="$4"
case_timeout="$5"
pass="$6"
. "$jail/mounts.sh"
export PATH="$jail/bin:/usr/bin:/bin"
export HOME="$jail/home"
USER="${USER:-root}"
export USER
export SUDO_USER="$USER"
cd "$subject_dir" || exit 1
case_index=0
while IFS= read -r line; do
    read -r -a case_args <<<"$line"
    case_index=$((case_index + 1))
    # Bounded, and with stdin closed. Both matter: a subject that reads stdin
    # blocks forever on the caller's terminal (a `crontab -` fallback did
    # exactly this and hung a run for the full two minutes with no output),
    # and a subject that spins never yields at all. A timed-out case is
    # reported rather than swallowed, because a silent timeout looks
    # identical to an unreachable line in the coverage report.
    if [[ $pass == kcov ]]; then
        timeout --kill-after=10s "$case_timeout" \
            kcov --include-pattern="$measure_base" "$jail/cov" \
            "./$subject_base" ${case_args[@]+"${case_args[@]}"} \
            >/dev/null 2>&1 </dev/null
        rc=$?
    else
        # PS4 carries the full BASH_SOURCE, not ${BASH_SOURCE##*/}: two libs
        # in different directories can share a basename, and the report
        # filters by basename itself.
        #
        # The trace fd is opened HERE and inherited, so the subject's own
        # stdout/stderr redirections (the jail sends both to /dev/null)
        # cannot swallow the trace -- a 2>/dev/null once cost a bogus
        # "0 lines traced" reading.
        timeout --kill-after=10s "$case_timeout" \
            env "BASH_XTRACEFD=199" "BASH_ENV=$jail/xtrace_env.sh" \
            "./$subject_base" ${case_args[@]+"${case_args[@]}"} \
            >/dev/null 2>&1 </dev/null 199>>"$jail/trace/case.$case_index"
        rc=$?
    fi
    if [[ $rc -eq 124 || $rc -eq 137 ]]; then
        printf 'warn: case timed out after %s: %s\n' "$case_timeout" "$line" >&2
        printf '%s\n' "$rc" >>"$jail/case_failures.$pass"
    elif [[ $rc -ne 0 ]]; then
        # A non-zero case is only noise when measuring (an installer that
        # exits 1 on a bogus arg still yields coverage), but it is the whole
        # signal when the subject is a TEST SUITE. Record it and let the
        # caller decide; swallowing it made a deliberately-broken assertion
        # exit 0 through the push gate.
        printf 'warn: case exited %d: %s\n' "$rc" "$line" >&2
        printf '%s\n' "$rc" >>"$jail/case_failures.$pass"
    fi
done <"$jail/cases"
INNER
	chmod +x "$JAIL/run_cases.sh"
}

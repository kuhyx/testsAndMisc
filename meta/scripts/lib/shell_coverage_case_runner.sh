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
. "$jail/mounts.sh"
export PATH="$jail/bin:/usr/bin:/bin"
export HOME="$jail/home"
USER="${USER:-root}"
export USER
export SUDO_USER="$USER"
cd "$subject_dir" || exit 1
while IFS= read -r line; do
    read -r -a case_args <<<"$line"
    # Bounded, and with stdin closed. Both matter: a subject that reads stdin
    # blocks forever on the caller's terminal (a `crontab -` fallback did
    # exactly this and hung a run for the full two minutes with no output),
    # and a subject that spins never yields at all. A timed-out case is
    # reported rather than swallowed, because a silent timeout looks
    # identical to an unreachable line in the coverage report.
    timeout --kill-after=10s "$case_timeout" \
        kcov --include-pattern="$measure_base" "$jail/cov" \
        "./$subject_base" ${case_args[@]+"${case_args[@]}"} \
        >/dev/null 2>&1 </dev/null
    rc=$?
    if [[ $rc -eq 124 || $rc -eq 137 ]]; then
        printf 'warn: case timed out after %s: %s\n' "$case_timeout" "$line" >&2
        printf '%s\n' "$rc" >>"$jail/case_failures"
    elif [[ $rc -ne 0 ]]; then
        # A non-zero case is only noise when measuring (an installer that
        # exits 1 on a bogus arg still yields coverage), but it is the whole
        # signal when the subject is a TEST SUITE. Record it and let the
        # caller decide; swallowing it made a deliberately-broken assertion
        # exit 0 through the push gate.
        printf 'warn: case exited %d: %s\n' "$rc" "$line" >&2
        printf '%s\n' "$rc" >>"$jail/case_failures"
    fi
done <"$jail/cases"
INNER
	chmod +x "$JAIL/run_cases.sh"
}

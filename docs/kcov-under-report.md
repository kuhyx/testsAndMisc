# kcov under-reports shell coverage: two distinct defects

Split out of `docs/shell-split-verification.md` on 2026-08-22 to hold both
files under the repo's 250-line cap. This is the campaign's instrument
problem; read it before trusting any coverage percentage.

### kcov silently under-reports some subjects: never trust a percentage alone

`rpi_nc_install.sh` measures **10/88 = 11.36%** under
`meta/scripts/shell_coverage_jail.sh`, reporting lines 13–60 as covered and
everything from 61 on as not. The code past line 61 provably runs: the suite's
29 assertions pass, and both `/root/.nextcloud_db_password` (line 61) and
`/etc/apache2/sites-available/nextcloud.conf` (a heredoc ending at line 100)
exist on disk after a run. The two sibling libs in the same directory measure
sensibly, so this is not universal — and nobody has bounded which subjects it
affects.

**Five hypotheses have each been tested against a minimal reproduction and
DISPROVEN. Do not retry them:**

1. kcov traces correctly **past a heredoc**.
2. kcov traces correctly **into a `$(...)` command substitution**.
3. kcov traces correctly **past a heredoc-fed stub reading stdin via `$(cat)`**.
4. kcov traces correctly **past a `cd` that relocates the process** (including
   `cd /tmp`, where the jail's own working dir lives) — lines after the `cd`
   are recorded.
5. kcov traces correctly **past a heredoc piped into a stubbed external** —
   `mysql -u root <<EOF` with a `cat >/dev/null` stub, under strict mode.
   Lines after it are recorded.

**One CONFIRMED artifact (hypothesis 6), reproduced minimally:** kcov counts
the _continuation lines of a multi-line quoted argument_ as instrumentable
statements that never run. A `perl -0777 -i -pe '<newline>...s!a!b!;<newline>'`
block reports its inner lines at zero hits while the line after it is covered.
This accounts for `dwm_config.sh` lines 64-66 and 98-101, and for any
`done < <(...)` process substitution. These lines are **not statements**, so
the denominator is wrong, not the numerator.

That artifact does NOT explain the second pattern: ordinary statements inside
functions that provably execute. In `dwm_config.sh`, `build_install`,
`build_pointer_confine`, `write_session_files` and `verify` all run -- proved
with an `exit 43` sentinel placed after their assertions, which fired -- yet
their bodies report zero hits. `rpi_nc_install.sh` behaves the same way. A
sixth hypothesis (that the jail's `exec`-ing `sudo` shim or a pipeline loses
the trace) was tested minimally and **DISPROVEN**: both trace correctly.

**The second pattern is a NUMERATOR bug, and an independent instrument proves
it.** Driving `rpi_nc_install.sh` directly under `PS4='+PS4:${BASH_SOURCE##*/}:${LINENO} '`
with `set -x`, 55 distinct lines of the lib trace as executed -- including
61, 62, 63, 66, 68, 102, 118 and 146, every one of which kcov reports as
uncovered. 45 of kcov's "uncovered" lines were seen executing this way. The
lines run; kcov does not record them.

So there are two separate defects, and they need different fixes:

- **(a) wrong denominator** -- continuation lines inside a multi-line quoted
  argument are counted as statements. A `bash -x` tracer never reports them as
  executable at all. Fixable in `meta/scripts/shell_coverage_report.py` by
  excluding them; affects `dwm_config.sh`'s perl blocks.
- **(b) wrong numerator** -- ordinary statements execute but are not recorded.
  This is what caps `rpi_nc_install.sh` at 11.36% and no test can move it.
  Fixing it means replacing or supplementing kcov's numerator with a PS4 /
  `DEBUG`-trap tracer.

A PS4 tracer inside the jail needs its output on a path the caller controls:
`/root` and `/var` are both bind-mounted to throwaway dirs, and the jail sends
each case's stdout to `/dev/null`.

The practical rule while both stand:

> **A suspicious percentage means re-measure, not re-write the test.** If a
> suite's assertions pass while its number looks absurd, suspect the
> instrument before suspecting the tests. **Never "fix" a number by weakening
> an assertion.**

Note the failure is _silent and one-directional_: it under-reports, so it can
only ever keep a lib on the allowlist that deserves to come off. It cannot
promote an untested lib. That is why the campaign can continue around it.

**The under-report is contagious across processes in one jail.** Measured on
`rpi_nc_ca.sh`: run alone its suite reports **73/73 = 100.00%**, reproduced
twice. Run through `run_all.sh` it reports **72/73 = 98.63%**, also twice --
and bisecting the five sibling suites shows a single culprit, `test_dwm_config.sh`.
Run `dwm_config` first and `rpi_nc_ca` loses line 141 (`cat <<'EOF'`, an
ordinary statement); run any other sibling first and it keeps it. The CA
suite's assertions all pass either way, confirmed with an exit sentinel, so
nothing is actually untested.

This matters for the gate: `is_covered()` measures through `run_all.sh`, so
the _runner's_ number is the one that counts, and it can be lower than the
same suite's own number for reasons that have nothing to do with the tests.
Never report the single-file figure as the lib's coverage.

**Use an `exit <n>` sentinel to tell the two apart.** The jail discards a
case's stdout, so a suite's own report is invisible; but a non-zero exit is
surfaced by `--fail-on-case-error`. Temporarily ending the suite with
`exit 42` at a chosen point turns "did execution reach here?" into a yes/no
the jail will answer. That is what proved the second pattern is a tracing
failure and not an aborted suite.

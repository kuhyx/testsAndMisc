# kcov under-reports shell coverage: two distinct defects

> **RESOLVED 2026-08-22.** Both defects are fixed; the instrument now
> corrects for them and the numbers below are the _historical_ readings that
> motivated the work. Kept because the disproven hypotheses are still worth
> not retrying, and because the two root causes are the kind that silently
> come back. What the fix does, and the three findings that make it work, is
> at the end of this file under "How it was fixed".

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

## How it was fixed (2026-08-22)

The instrument now runs **two passes over the same cases, in two fresh
namespaces**, and combines them:

- **denominator** = kcov's instrumentable line set, minus continuation lines
  of multi-line quoted arguments (defect (a), detected by tracking quote
  state across the file in `meta/scripts/lib/shell_coverage_lines.py`);
- **numerator** = (PS4-traced lines ∪ kcov's own hits) ∩ denominator
  (defect (b)).

The trace cannot supply the denominator. A trace only ever reports lines that
_ran_, so using it for both halves would make every subject 100.00% and gate
on nothing. kcov's line set is what keeps the gate meaningful; kcov's _hits_
are what could not be trusted.

### Three findings, each of which silently produces a WRONG trace

1. **kcov and xtrace cannot share a process.** Under `SHELLOPTS=xtrace`,
   every line kcov had recorded as `hits="1"` comes back `hits="0"` —
   reproduced minimally, A/B, on the same subject. Hence two passes.
2. **`SHELLOPTS` is a readonly variable inside bash.** `export
SHELLOPTS=xtrace` fails with "readonly variable" and tracing never turns
   on. It only works placed in the environment _of_ the process.
3. **Decisive: bash under `unshare --user --map-root-user` runs in PRIVILEGED
   mode and DISCARDS an inherited `PS4`**, falling back to the default `+ `,
   while still honouring `SHELLOPTS=xtrace` and `BASH_XTRACEFD`. The trace
   then carries no `file:line` prefix at all, so every subject reads as 0%
   covered. This is why the trace is delivered through a **`BASH_ENV` file**
   that assigns `PS4` and runs `set -x` from _inside_ each shell — which also
   solves propagation into child processes, since `set -x` does not inherit.

A fourth trap, in the report rather than the jail: **kcov records
`filename="dwm_config.sh"`, a bare basename, not a path.** The source
location has to come from the trace (which carries `${BASH_SOURCE}`) or from
a repo search; an ambiguous basename yields no exclusion rather than a guess.

### Measured effect, all through `run_all.sh`

| lib                       | before          | after                        |
| ------------------------- | --------------- | ---------------------------- |
| `dot_resolver_install.sh` | 39/39 = 100.00% | 39/39 = 100.00% (acceptance) |
| `rpi_nc_ca.sh`            | 72/73 = 98.63%  | **73/73 = 100.00%**          |
| `dwm_config.sh`           | 35/73 = 47.95%  | **65/66 = 98.48%**           |
| `rpi_nc_install.sh`       | 10/88 = 11.36%  | **85/88 = 96.59%**           |

`rpi_nc_ca.sh` reaching 100.00% is the load-bearing check: its missing line
141 was the _cross-process contagion_ described above, and the trace pass has
no kcov in it to be contaminated. Nothing went down.

`dwm_config.sh`'s remaining uncovered line 39 is a `done < <(...)` process
substitution — the other half of defect (a). It is deliberately still in the
denominator: every line removed from a denominator inflates coverage, which
is the fail-open direction, so a second exclusion rule should be justified
per line rather than generalised from one lib.

## Defect (c): kcov's LINE SET is also incomplete — bounded, and fail-closed

The report prints, per subject, any line the trace saw execute that kcov never
listed as instrumentable at all:

```
outside kcov's line set (ran, but counted in neither half): 68, 70, 73, ...
```

Measured across every lib with a harness, these fall into two classes:

- **Not statements, correctly absent.** `dwm_config.sh:27` (`heal_config() {`,
  a function declaration), `transcribe_deps.sh:9` (a one-line function
  declaration), `clean_audio_filters.sh:197,200` (`((running++))`).
- **Ordinary statements, wrongly absent.** `aw_autostart.sh` lines 68, 70, 73,
  79-81, 83-84, 87-88, 94 — plain `echo`, `local`, `if [[ ... ]]`, `sudo -u
... mkdir` and a `cat >` heredoc. The trigger is a `{ ... } >>"$file"`
  command group with a redirection at lines 61-65: kcov lists nothing after it
  in that function.

**This cannot inflate a percentage, and cannot hide an untested line.** A line
only reaches that list _because the trace saw it run_. Folding all 11 of
`aw_autostart.sh`'s into both halves moves it from 80/82 = 97.56% to
91/93 = 97.85% — up, not down. The direction is structural: an off-set line is
by construction an executed line, so it can only ever be a missing _covered_
line, never a missing _uncovered_ one.

What it does mean is that a subject with off-set lines is measured over a
SUBSET of its statements. The percentage is honest about the subset; it is not
a claim about the whole file. Read the list before clearing such a lib off the
allowlist.

## `nc_php.sh` does not measure at all, on either instrument

`nc_php.sh` reports "kcov instrumented no lines" — reproduced twice on the
current instrument and once on the pre-fix instrument at commit `078d3463`,
via a throwaway worktree. It is **not** a regression from the two-pass change.
The 84/85 = 98.82% in earlier notes does not reproduce; whatever produced it
is not what `run_all.sh` does today. `test_nc_php.sh` exists and runs. Treat
the old figure as unverified and re-derive it before relying on it.

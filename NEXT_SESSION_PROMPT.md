# Next session: fix the coverage INSTRUMENT, then keep clearing the allowlist

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## Status in one table

| Thing                           | Number                                 |
| ------------------------------- | -------------------------------------- |
| In-scope shell libs             | **201**                                |
| Passing the gate today          | **98**                                 |
| Still allowlisted (exempt)      | **103**                                |
| Directories with a test harness | 7                                      |
| Cleared this session            | 2 (`unity_handler`, `transcribe_venv`) |

The gate itself is **built and ready to arm**. `is_covered()` reads `jail_args`
and passes `--fail-on-case-error`. Only the allowlist stands between here and
wiring it into pre-commit, pre-push and CI. CI is green.

## The scoping answers are SETTLED. Do not re-ask them.

Repo-wide gate (not a ratchet) · **100%** line coverage · **ALL** `.sh` ·
pre-commit **AND** pre-push **AND** CI · tests first, arm the gate last ·
hardest first.

## START HERE — the instrument is the bottleneck, not the tests

**kcov has two separate defects. One is fixable today; the other caps libs at
numbers no test can move.** Full detail and the seven DISPROVEN hypotheses are
in `docs/kcov-under-report.md` — read it first and do not retry them.

- **(a) Wrong denominator.** Continuation lines inside a multi-line quoted
  argument (a `perl -0777 -pe '...'` block) are counted as statements. A
  `bash -x` tracer never reports them as executable at all. This is what holds
  `dwm_config.sh` down.
- **(b) Wrong numerator.** Ordinary statements execute but are not recorded.
  **Proven against an independent instrument:** driving `rpi_nc_install.sh`
  under `PS4='+PS4:${BASH_SOURCE##*/}:${LINENO} '` with `set -x`, 55 lines
  trace as executed, and **45 of them are lines kcov calls uncovered** —
  including 61, 62, 63, 66, 68, 102, 118, 146. This is why that lib sits at
  11.36% while all 29 of its assertions pass.

### Step 1 — fix (a) in `meta/scripts/shell_coverage_report.py`

Exclude continuation lines of multi-line quoted arguments from the
denominator. It already parses the kcov XML and has the source path from the
`filename` attribute, so this is a local change.

### Step 2 — fix (b) by replacing kcov's numerator with a PS4 tracer

Inside the jail the trace must land on a path the caller controls: `/root` and
`/var` are both bind-mounted to throwaway dirs, and `shell_coverage_jail.sh`
sends every case's stdout to `/dev/null`. Bind a dedicated output dir, or
teach the jail to copy the trace out before teardown.

### Acceptance test for ANY instrument change

```bash
# must still be 39/39 = 100.00%
--measure dot_resolver_install.sh --min 100
# must not regress below 98.63%
--measure rpi_nc_ca.sh
```

If either moves the wrong way, the change is wrong. Both are measured through
`run_all.sh`, never a single test file.

## If the instrument work stalls, there is always forward motion

Two directories have libs and no harness at all:

```
22 libs  linux_configuration/scripts/single_use/fixes/lib/
 9 libs  phone_focus_mode/lib/
41 libs  linux_configuration/scripts/single_use/features/lib/   (harness exists)
```

Building a harness for `fixes/lib` unblocks 22 libs at once, the way this
session's `testsAndMisc-bash` harness unblocked 5.

## The invocation that works

```bash
bash -c '
ja=(); while IFS= read -r l; do ja+=("$l"); done \
  < <(grep -v "^#\|^$" linux_configuration/scripts/single_use/features/lib/tests/jail_args)
timeout 300s bash meta/scripts/shell_coverage_jail.sh \
  --subject linux_configuration/scripts/single_use/features/lib/tests/run_all.sh \
  "${ja[@]}" --measure <lib>.sh --min 1 --fail-on-case-error -- ""'
```

**Always measure through `run_all.sh`, never a single test file.** That is the
subject `is_covered()` builds, and the runner's number can be LOWER than the
suite's own — `rpi_nc_ca.sh` is 100% alone and 98.63% through the runner.

A suite declares its jail needs in a **`jail_args`** file beside its
`run_all.sh`; `ci_mirror.sh`, `shell-tests.yml` and `is_covered()` all read it.
No marker means the suite runs bare.

## Measured so far (all through `run_all.sh`)

| lib                       | coverage            | state         |
| ------------------------- | ------------------- | ------------- |
| `dot_resolver_install.sh` | **39/39 = 100.00%** | off allowlist |
| `unity_handler.sh`        | **32/32 = 100.00%** | off allowlist |
| `transcribe_venv.sh`      | **53/53 = 100.00%** | off allowlist |
| `rpi_nc_ca.sh`            | 72/73 = 98.63%      | allowlisted   |
| `nc_php.sh`               | 84/85 = 98.82%      | allowlisted   |
| `transcribe_pkgmgr.sh`    | 49/50 = 98.00%      | allowlisted   |
| `transcribe_deps.sh`      | 48/52 = 92.31%      | allowlisted   |
| `clean_audio_filters.sh`  | 83/93 = 89.25%      | allowlisted   |
| `aw_autostart.sh`         | 68/82 = 82.93%      | allowlisted   |
| `dwm_config.sh`           | 35/73 = 47.95%      | defect (a)    |
| `rpi_nc_install.sh`       | 10/88 = 11.36%      | defect (b)    |

The last two are instrument-limited, not test-limited. **Writing more tests
for them will not move the number** — their assertions already pass and their
writes provably land on disk.

## Traps that cost real time

- **`--fail-on-case-error` or you are flying blind.** The jail suppresses a
  suite's stdout, so assertions fail invisibly without it.
- **To find WHERE a suite dies, use an `exit <n>` sentinel.** Temporarily end
  the suite with `exit 42`; the jail surfaces the code. The only way to tell a
  tracing failure from an aborted suite.
- **`rm -f "$TEST_TMPDIR/bin/foo"` does NOT hide foo.** bash caches executable
  locations. Both harnesses ship `_t_unstub`, which also runs `hash -r`. Three
  assertions in this repo were asserting the opposite of their own names.
- **A prepended stub dir cannot hide a real binary.** If the host genuinely has
  the tool (`pacman`, `aw-qt`, `/usr/lib/libsndfile.so`), REPLACE PATH or jail
  it, or the "not installed" case tests nothing.
- **A stub must materialise what the real tool creates.** A record-only stub in
  a `[[ ! -s $file ]]` fallback chain silently exercises the NEXT branch.
- **A top-level stub function SHADOWS the subject's own** for every later
  assertion. Put redefinitions in a subshell.
- **`2>/dev/null` swallows a PS4 trace too** — it cost a bogus "0 lines traced"
  reading before the redirect was noticed.
- **`shfmt` reformats after your own check passes** — re-check the 250-line cap
  after staging.
- **Commits exceed a 2-minute foreground timeout.** Use `run_in_background`.
- **Two-strike rule.** Two failed attempts at the same thing -> stop, document,
  keep the working state.

## Rules that will bite you

- **No suppressions, ever.** Fix SC2016/SC2155 at the source.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (validate with
  `python3 meta/scripts/validate_evidence.py <file>`), **plus a contract** in
  `docs/superpowers/contracts/` once **>=4 code files** are staged.
- **Put the MEASURED number in it**, never a rounded or hoped-for one.
- **Stage narrowly.** A concurrent session had 8 unrelated files in the shared
  index this session; `git restore --staged` them.
- **New test files need the exec bit** — `git add --chmod=+x` only changes the
  INDEX; `chmod +x` the working tree too or the shebang hook fails.
- **`CI_GREEN_SKIP=1`** is the documented escape hatch when THIS commit fixes a
  red baseline. Export it for the pre-push mirror too.
- Work directly on `main`. `git stash` and branch creation are blocked.
- **Another Claude session may be working in this repo simultaneously.**

## Not caused by this campaign

**`Python tests` CI has been failing since 2026-08-17** — `pip` hits
`error: resolution-too-deep` installing `meta/requirements.txt`. Needs
dependency pinning; deliberately excluded from `check_ci_green.sh`. Do not
fold it into this work.

## When the allowlist reaches zero

Wire `check_shell_coverage.sh` into pre-commit, pre-push and CI. The gate is
already correct; it runs a full jailed suite per lib, so an `--all` sweep is
minutes and belongs in CI, not a commit hook.

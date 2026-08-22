# Next session: the instrument is FIXED — go clear the allowlist

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## What changed: the bottleneck is gone

The previous handoff said "the instrument is the bottleneck, not the tests."
That is **no longer true**. Both kcov defects are fixed and pushed
(`81191f40`, `29b8c5a7`). The two libs that were pinned at absurd numbers were
never test-limited:

| lib                       | was             | now                 |
| ------------------------- | --------------- | ------------------- |
| `dwm_config.sh`           | 35/73 = 47.95%  | **65/66 = 98.48%**  |
| `rpi_nc_install.sh`       | 10/88 = 11.36%  | **85/88 = 96.59%**  |
| `rpi_nc_ca.sh`            | 72/73 = 98.63%  | **73/73 = 100.00%** |
| `aw_autostart.sh`         | 68/82 = 82.93%  | **80/82 = 97.56%**  |
| `clean_audio_filters.sh`  | 83/93 = 89.25%  | **85/93 = 91.40%**  |
| `dot_resolver_install.sh` | 39/39 = 100.00% | 39/39 = 100.00%     |

Nothing went down. **Every allowlisted lib is worth re-measuring before you
write a single new test** — several are probably already at or near 100%.

## How the instrument works now (read before changing it)

Coverage = `(PS4-traced lines | kcov hits) & (kcov line set - continuation lines)`

Two passes over the same cases, in two fresh namespaces. They **cannot** be
merged: kcov's ptrace and bash's xtrace are mutually exclusive — under
`SHELLOPTS=xtrace` every line kcov recorded as `hits="1"` comes back
`hits="0"`, measured A/B.

**The trace must never supply the denominator.** A trace reports only lines
that RAN, so trace-as-denominator makes every subject 100.00% and gates on
nothing. kcov's line set is what keeps the gate meaningful.

Full detail, including the three findings that each yield a silently wrong
trace, is in `docs/kcov-under-report.md`. The load-bearing one: **bash under
`unshare --map-root-user` runs privileged and DISCARDS an inherited `PS4`**,
so tracing is delivered through a `BASH_ENV` file instead.

## The scoping answers are SETTLED. Do not re-ask them.

Repo-wide gate (not a ratchet) · **100%** line coverage · **ALL** `.sh` ·
pre-commit **AND** pre-push **AND** CI · tests first, arm the gate last ·
hardest first.

## START HERE — re-measure the allowlist

98 libs are allowlisted on numbers produced by a broken instrument. Sweep
them with the fixed one before writing tests. The invocation:

```bash
bash -c '
ja=(); while IFS= read -r l; do ja+=("$l"); done \
  < <(grep -v "^#\|^$" <suite>/tests/jail_args)
timeout 900s bash meta/scripts/shell_coverage_jail.sh \
  --subject <suite>/tests/run_all.sh \
  "${ja[@]}" --measure <lib>.sh --min 1 --fail-on-case-error -- ""'
```

Omit the `ja` array entirely for suites with no `jail_args` (transcribe,
fixes) — those confine their writes to a `mktemp -d` and run bare.

**Always measure through `run_all.sh`, never a single test file.** That is the
subject `is_covered()` builds.

## Directories and their harness state

```
41 libs  linux_configuration/scripts/single_use/features/lib/   harness + jail_args
 5 libs  .../misc/testsAndMisc-bash/lib/                        harness, no jail_args
22 libs  .../single_use/fixes/lib/       run_all.sh ADDED this session; 6 of 22 tested
 9 libs  phone_focus_mode/lib/                                  NO harness
```

`fixes/lib` was listed as "no harness at all" in the previous handoff. That
was wrong — 8 test files and 2 harnesses already existed; what was missing was
`run_all.sh`, which is what `is_covered()` measures through. It now exists and
all 8 test files pass through it. **16 of the 22 libs there still have no
tests at all** — that is the largest remaining block of real test-writing work.

## Already measured this session — do NOT redo these

All through `run_all.sh` on the fixed instrument. `fixes/lib` needs no
`jail_args`; the features libs use the one beside their `run_all.sh`.

| lib                            | coverage            | note                      |
| ------------------------------ | ------------------- | ------------------------- |
| `rpi_nc_ca.sh`                 | **73/73 = 100.00%** | measured 3x, solid        |
| `dot_resolver_install.sh`      | **39/39 = 100.00%** | acceptance baseline       |
| `pacman_hook_stall_capture.sh` | **59/59 = 100.00%** | fixes/lib                 |
| `pacman_hook_stall_load.sh`    | **25/25 = 100.00%** | fixes/lib                 |
| `pacman_hook_stall_summary.sh` | **18/18 = 100.00%** | fixes/lib; off-set: 36    |
| `pacman_hook_stall_watch.sh`   | **24/24 = 100.00%** | fixes/lib                 |
| `pacman_hook_stall_usage.sh`   | **1/1 = 100.00%**   | body is one heredoc       |
| `dwm_config.sh`                | 65/66 = 98.48%      | line 39 is `done < <(…)`  |
| `pacman_hook_stall_setup.sh`   | 26/27 = 96.30%      | uncovered: 7              |
| `aw_autostart.sh`              | 80/82 = 97.56%      | 11 off-set lines          |
| `rpi_nc_install.sh`            | 85/88 = 96.59%      | uncovered: 70, 202, 216   |
| `transcribe_pkgmgr.sh`         | 49/50 = 98.00%      | uncovered: 42             |
| `clean_audio_filters.sh`       | 85/93 = 91.40%      | uncovered incl. 52-58     |
| `transcribe_deps.sh`           | 48/52 = 92.31%      | uncovered: 19, 52, 53, 55 |

**Five were CLEARED this session** (`83de41f4`): the pacman_hook_stall libs
`capture`, `load`, `summary`, `usage` and `watch`. Each was measured twice,
the second time gating at `--min 100`, then confirmed through the real
`check_shell_coverage.sh` with no exemption — all exit 0. **Allowlist:
103 -> 98.**

`rpi_nc_ca.sh` and `dot_resolver_install.sh` are also at 100.00% and measured
3x / 2x, but they live in `features/lib`, where 39 other libs are still
allowlisted. Removing them is safe by the same standard whenever you want.

The bar to reuse: **two matching runs, the second at `--min 100`, then the
real gate.** `fixes/lib`'s suites drive `watch_forever` timing loops, and a
timing-dependent suite can vary its line set run to run (`dwm_config.sh` was
seen to). A flaky 100% becomes a red CI job whose cause is invisible.

Allowlist entries are **static per-file lines**, verified: adding
`fixes/lib/tests/run_all.sh` did NOT start failing the 16 untested libs in
that directory — `check_shell_coverage.sh <one of them>` still exits 0,
because each is listed explicitly. The allowlist header's "every file in that
directory is enforced" describes intent, not current mechanics.

## Two instrument bounds you must know

**Defect (c): kcov's LINE SET is incomplete too.** The report now prints, per
subject, any line the trace saw run that kcov never listed:

```
outside kcov's line set (ran, but counted in neither half): 68, 70, 73, ...
```

This **cannot inflate a percentage**. A line reaches that list only because
the trace saw it EXECUTE, so folding them in only ever raises the number
(`aw_autostart.sh` 80/82 = 97.56% -> 91/93 = 97.85%). It can never hide an
untested line. What it does mean: such a subject is measured over a SUBSET of
its statements. Read the list before clearing that lib.

`aw_autostart.sh` is the known case — kcov lists nothing after the
`{ ... } >>"$file"` command group at lines 61-65.

**`nc_php.sh` does not measure at all.** "kcov instrumented no lines", on the
fixed instrument AND on the pre-fix one (checked at `078d3463` in a throwaway
worktree). Not a regression. The 84/85 = 98.82% in older notes does not
reproduce — treat it as unverified.

## Traps that cost real time

- **`--fail-on-case-error` or you are flying blind.** The jail suppresses a
  suite's stdout, so assertions fail invisibly without it.
- **To find WHERE a suite dies, use an `exit <n>` sentinel.** The jail
  surfaces the code. The only way to tell a tracing failure from an abort.
- **`rm -f "$TEST_TMPDIR/bin/foo"` does NOT hide foo.** bash caches executable
  locations. Use the harnesses' `_t_unstub`, which also runs `hash -r`.
- **A prepended stub dir cannot hide a real binary.** If the host genuinely
  has the tool, REPLACE PATH or jail it.
- **A stub must materialise what the real tool creates.** A record-only stub
  in a `[[ ! -s $file ]]` chain silently exercises the NEXT branch.
- **A top-level stub function SHADOWS the subject's own** for every later
  assertion. Put redefinitions in a subshell.
- **`shfmt` and `prettier` reformat after your own check passes** — re-check
  the 250-line cap after staging, and expect the pre-push prettier hook to
  reject markdown you hand-formatted.
- **Commits and pushes exceed a 2-minute foreground timeout.** Background them.
- **Never edit the working tree while a measurement runs.** The jail
  fingerprints `git status --porcelain` before each case and aborts with
  "the subject modified the working tree; a write escaped the jail" if it
  changed. Editing an unrelated file mid-run produces that error and it is a
  FALSE alarm — cost two runs this session, twice.
- **A sweep's output file buffers.** `pgrep -f shell_coverage_jail` is the
  liveness signal, not file growth. A measurement that has printed nothing for
  minutes is usually still running; `fixes/lib`'s timing-loop suites take 30s+
  per kcov pass.
- **Two-strike rule.** Two failed attempts at the same thing -> stop, document,
  keep the working state.

## Rules that will bite you

- **No suppressions, ever.** Fix SC2016/SC2155/EXE001/PLR2004 at the source.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (validate with
  `python3 meta/scripts/validate_evidence.py <file>`), **plus a contract** in
  `docs/superpowers/contracts/` once **>=4 code files** are staged.
- **Put the MEASURED number in it**, never a rounded or hoped-for one.
- **Stage narrowly.** Another session may be working in this repo at the same
  time; `git restore --staged` anything you did not touch.
- **New test files need the exec bit** — `git add --chmod=+x` only changes the
  INDEX; `chmod +x` the working tree too or the shebang hook fails.
- Work directly on `main`. `git stash` and branch creation are blocked.

## When the allowlist reaches zero

Wire `check_shell_coverage.sh` into pre-commit, pre-push and CI. The gate is
already correct. Note it now runs each suite TWICE per lib, so an `--all`
sweep is roughly double what it was and belongs in CI, not a commit hook.

## Not caused by this campaign

**`Python tests` CI has been failing since 2026-08-17** — `pip` hits
`error: resolution-too-deep` installing `meta/requirements.txt`. Needs
dependency pinning; deliberately excluded from `check_ci_green.sh`. Do not
fold it into this work.

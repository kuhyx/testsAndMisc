# Next session: test the 16 untested `fixes/lib` libs to 100%

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The job

`linux_configuration/scripts/single_use/fixes/lib/` has 22 libs. Six are done
and off the allowlist. **Sixteen have no tests at all.** Write them, to 100%
line coverage, and take each one off `meta/shell-coverage-allowlist.txt`.

That is the largest remaining block of real test-writing work in the campaign.

| lines | lib                       | family                                 |
| ----- | ------------------------- | -------------------------------------- |
| 215   | `ubuntu_perf_fixes.sh`    | ubuntu perf                            |
| 214   | `bt_audio.sh`             | bluetooth (`fix_bluetooth.sh`)         |
| 202   | `arch_hardware.sh`        | arch perf (`optimize_arch_desktop.sh`) |
| 180   | `nvidia_config.sh`        | arch perf                              |
| 179   | `thorium_repairs.sh`      | standalone                             |
| 166   | `arch_perf_probes.sh`     | arch perf                              |
| 161   | `hosts_guard_migrate.sh`  | hosts guard                            |
| 150   | `bt_adapter.sh`           | bluetooth                              |
| 141   | `hosts_guard_rollback.sh` | hosts guard                            |
| 128   | `bt_pairing.sh`           | bluetooth                              |
| 126   | `arch_cpu.sh`             | arch perf                              |
| 122   | `arch_sysctl.sh`          | arch perf                              |
| 121   | `arch_perf_fixes.sh`      | arch perf                              |
| 103   | `arch_perf_report.sh`     | arch perf                              |
| 80    | `ubuntu_perf_more.sh`     | ubuntu perf                            |
| 76    | `bt_report.sh`            | bluetooth                              |

**Suggested order: smallest first, by family.** `bt_report.sh` (76) then the
rest of the bluetooth four; the arch-perf six share `optimize_arch_desktop.sh`
and will share stubs. Do not start with `ubuntu_perf_fixes.sh`.

## Everything you need already exists — do NOT build a new harness

`fixes/lib/tests/` is a working suite. It has:

- `run_all.sh` — the runner. **This is the subject the gate measures through.**
- `pacman_hook_stall_harness.sh` (205 lines) — lib-level harness: `mktemp -d`
  sandbox, a `FAKE_BIN` PATH stub dir, `_t_eq` / `_t_pass` / `_t_fail`,
  and `_t_unstub` (which also runs `hash -r`).
- `pacman_hook_stall_entry_harness.sh` (142 lines) — same for entry scripts.
- Eight `test_*.sh` files to copy the shape from.

**jscpd fails the commit above 2% duplication**, so extend/parameterise these
rather than cloning a harness per family. If a family genuinely needs
different setup, add a small harness that _sources_ the existing one.

No `jail_args` file sits beside `run_all.sh`, deliberately: the harness
confines every write to its own `mktemp -d` and stubs external commands on
PATH. Keep it that way — the new tests must not write to `/etc`, `/var` or
`/usr`. If a lib insists on writing an absolute path, stub the writer, do not
add a bind mount.

## What these libs touch (drives your stubs)

`systemctl` (most common), `bluetoothctl`, `pacman`, `sysctl`, `sudo`,
`nvidia-*`, `apt-get`. `systemctl`, `pacman` and `sudo` are already in the
jail's `DEFAULT_SHIMS`; the rest you stub in `FAKE_BIN`.

Two entry scripts source these libs, and are the place to look for how each
lib is really called:

- `linux_configuration/scripts/single_use/fixes/fix_bluetooth.sh`
- `linux_configuration/scripts/single_use/fixes/optimize_arch_desktop.sh`

## The loop, per lib

```bash
# 1. write tests/test_<lib>.sh, chmod +x it
# 2. run the suite bare first -- much faster than the jail
bash linux_configuration/scripts/single_use/fixes/lib/tests/run_all.sh

# 3. then measure through the runner, in the jail
timeout 900s bash meta/scripts/shell_coverage_jail.sh \
  --subject linux_configuration/scripts/single_use/fixes/lib/tests/run_all.sh \
  --measure <lib>.sh --min 1 --fail-on-case-error -- ""

# 4. close the gap, repeat until 100.00%
```

**Always measure through `run_all.sh`, never a single test file.** That is the
subject `is_covered()` builds, and the runner's number can be LOWER than a
suite's own.

## The bar for taking a lib off the allowlist

Do all three. This is the standard the five cleared libs met:

1. Measure 100.00% through `run_all.sh`.
2. **Measure again at `--min 100`** so a shortfall is a non-zero exit rather
   than a number you might misread.
3. Remove the line from `meta/shell-coverage-allowlist.txt`, then run the real
   gate with no exemption and confirm exit 0:
   ```bash
   bash meta/scripts/check_shell_coverage.sh <path to lib>.sh
   # expect: "every checked shell library meets the coverage bar"
   ```

Two matching runs matters: this directory's suites drive timing loops, and a
timing-dependent suite can vary its line set between runs (`dwm_config.sh` was
observed doing exactly that). A flaky 100% becomes a red CI job whose cause is
invisible.

Allowlist is at **98** entries. Each lib you finish takes it down by one.

## The instrument is FIXED — trust its numbers now

Coverage = `(PS4-traced lines | kcov hits) & (kcov line set - continuation lines)`

Two passes, two namespaces, because kcov's ptrace and bash's xtrace cannot
share a process. Full detail in `docs/kcov-under-report.md`. You should not
need to touch it. If you do, the acceptance test is
`dot_resolver_install.sh` = 39/39 and `rpi_nc_ca.sh` = 73/73, and **no lib's
percentage may go DOWN** — a drop means a lost trace, not a stricter
instrument.

One bound to know: the report may print

```
outside kcov's line set (ran, but counted in neither half): 68, 70, ...
```

That **cannot inflate a number** — such a line is by construction one the
trace saw execute, so folding it in only ever raises the figure. It does mean
the lib is measured over a subset of its statements. Read the list before
clearing that lib; if the lines are ordinary statements, say so in the
evidence.

## Traps that cost real time

- **Never edit the working tree while a measurement runs.** The jail
  fingerprints `git status --porcelain` and aborts with "a write escaped the
  jail". Editing an unrelated file trips it. FALSE alarm; cost two runs last
  session, the second time after it had already been diagnosed. Commit before
  starting a sweep; use the scratchpad for notes.
- **A sweep's output file buffers.** `pgrep -x kcov` is the liveness signal,
  not file growth. A measurement silent for minutes is usually still running;
  this directory's suites take 30s+ per kcov pass, and there are two passes.
- **Do not `pgrep -f shell_coverage_jail` in a wait loop** — the loop's own
  command line matches, so it never exits.
- **`--fail-on-case-error` or you are flying blind.** The jail suppresses the
  suite's stdout, so assertions fail invisibly without it.
- **To find WHERE a suite dies, use an `exit <n>` sentinel.** The jail
  surfaces the code. The only way to tell a tracing failure from an abort.
- **`rm -f "$TEST_TMPDIR/bin/foo"` does NOT hide foo.** bash caches executable
  locations. Use `_t_unstub`, which also runs `hash -r`.
- **A prepended stub dir cannot hide a real binary.** If the host genuinely
  has the tool, REPLACE PATH or jail it, or the "not installed" case tests
  nothing.
- **A stub must materialise what the real tool creates.** A record-only stub
  in a `[[ ! -s $file ]]` chain silently exercises the NEXT branch.
- **A top-level stub function SHADOWS the subject's own** for every later
  assertion. Put redefinitions in a subshell.
- **`shfmt` and `prettier` reformat after your check passes** — re-check the
  250-line cap after staging, and expect the pre-push prettier hook to reject
  hand-formatted markdown.
- **Commits and pushes exceed a 2-minute foreground timeout.** Background them.
- **Two-strike rule.** Two failed attempts at the same thing -> stop, document,
  keep the working state.

## Rules that will bite you

- **No suppressions, ever.** Fix SC2016/SC2155/EXE001/PLR2004 at the source.
- **Never weaken an assertion to move a number.** If a percentage looks absurd
  while assertions pass, suspect the instrument and re-measure.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (validate with
  `python3 meta/scripts/validate_evidence.py <file>`), **plus a contract** in
  `docs/superpowers/contracts/` once **>=4 code files** are staged.
- **Put the MEASURED number in it**, never a rounded or hoped-for one.
- **New test files need the exec bit** — `git add --chmod=+x` only changes the
  INDEX; `chmod +x` the working tree too or the shebang hook fails.
- **Stage narrowly.** Another session may be working in this repo at the same
  time; `git restore --staged` anything you did not touch.
- Work directly on `main`. `git stash` and branch creation are blocked.

## State as of 2026-08-22

Allowlist **98**. Instrument fixed and pushed (`81191f40`, `29b8c5a7`). Five
libs cleared (`83de41f4`). `fixes/lib/tests/run_all.sh` added (`347222b9`).

Already measured — do NOT redo:

| lib                          | coverage            |
| ---------------------------- | ------------------- |
| `rpi_nc_ca.sh`               | **73/73 = 100.00%** |
| `dot_resolver_install.sh`    | **39/39 = 100.00%** |
| `dwm_config.sh`              | 65/66 = 98.48%      |
| `pacman_hook_stall_setup.sh` | 26/27 = 96.30%      |
| `aw_autostart.sh`            | 80/82 = 97.56%      |
| `rpi_nc_install.sh`          | 85/88 = 96.59%      |
| `transcribe_pkgmgr.sh`       | 49/50 = 98.00%      |
| `clean_audio_filters.sh`     | 85/93 = 91.40%      |
| `transcribe_deps.sh`         | 48/52 = 92.31%      |

`rpi_nc_ca.sh` and `dot_resolver_install.sh` are at 100% and could come off
the allowlist whenever you want, by the three-step bar above.

**`nc_php.sh` does not measure at all** — "kcov instrumented no lines", on the
pre-fix instrument too (checked at `078d3463` in a throwaway worktree). Not a
regression. Its old 84/85 = 98.82% does not reproduce; treat as unverified.

## Not caused by this campaign

**`Python tests` CI has been failing since 2026-08-17** — `pip` hits
`error: resolution-too-deep` installing `meta/requirements.txt`. Needs
dependency pinning; deliberately excluded from `check_ci_green.sh`. Do not
fold it into this work.

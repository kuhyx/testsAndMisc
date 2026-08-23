# Next session: the last 2 untested `fixes/lib` libs

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The job

`linux_configuration/scripts/single_use/fixes/lib/` has 22 libs. **Two still
have no tests.** Write them, to 100% line coverage, and take each one off
`meta/shell-coverage-allowlist.txt`.

| lines | lib                    | entry script                | harness                                   |
| ----- | ---------------------- | --------------------------- | ----------------------------------------- |
| 215   | `ubuntu_perf_fixes.sh` | `fix_ubuntu_performance.sh` | `ubuntu_perf_harness.sh` — ALREADY EXISTS |
| 180   | `nvidia_config.sh`     | `nvidia_troubleshoot.sh`    | needs a new one                           |

**Do `ubuntu_perf_fixes.sh` first** — its harness already exists and already
exports `JOURNALD_CONF_DIR` and `UNDO_DIR`, so you extend rather than build.

Allowlist is at **86** entries — count with `grep -vc '^#'`, since the file
also holds comment lines.

## What the previous session finished

Allowlist **91 -> 86**, six commits. Five libs cleared:

| lib                       | coverage            |
| ------------------------- | ------------------- |
| `arch_cpu.sh`             | **57/57 = 100.00%** |
| `arch_hardware.sh`        | **94/94 = 100.00%** |
| `thorium_repairs.sh`      | **75/75 = 100.00%** |
| `hosts_guard_migrate.sh`  | **81/81 = 100.00%** |
| `hosts_guard_rollback.sh` | **65/65 = 100.00%** |

`arch_sysctl.sh` has 23 green assertions but is NOT cleared — see the
quarantine section below.

## Everything you need already exists — do NOT build a new harness

`fixes/lib/tests/` is a working suite: **28 test files, all green, all
shellcheck-clean with zero suppressions.** Layers:

- `run_all.sh` — the runner. **The subject the gate measures through.**
- `lib_test_core.sh` — shared primitives. Read it first. **240 lines, close to
  the 250-line cap: the next helper added here forces a split.**
  - `_t_eq` / `_t_contains` / `_t_lacks` / `_t_pass` / `_t_fail`
  - `_t_stub NAME BODY`, plus `_t_stub_stdin` (body from a quoted heredoc),
    `_t_stub_cat NAME FIXTURE`, `_t_stub_writes NAME ARGNUM CONTENT`. Use
    these instead of `_t_stub foo '...$1...'`, which trips SC2016 every time.
  - **`_t_run FUNC [ARG...]`** — runs FUNC in the CURRENT shell, puts combined
    output in `$out`, returns its status. **Use this, never `out="$(func)"`:**
    command substitution forks a subshell and kcov then does not register the
    sourced lib at all (measured: 0 lines via `$( )`, 54 via a direct call).
  - `_t_unstub NAME...` (runs `hash -r`; deleting the file alone does nothing)
  - **`_t_hide TOOL...`** — rebuilds PATH from symlinks to every real binary
    EXCEPT the named ones. It KEEPS `$FAKE_BIN` on PATH, so **`_t_unstub` the
    tool first** or the harness's own default stub still satisfies `has_cmd`
    and the "not installed" branch never runs. The farm is cached by tool
    list; it symlinks ~13.5k binaries and rebuilding it per call cost enough
    runtime to blow a jail timeout.
  - `_t_calls` / `_t_reset_calls` — what the stubs recorded.
- **Five family harnesses**: `bt_harness.sh`, `arch_perf_harness.sh`,
  `arch_desktop_harness.sh`, `ubuntu_perf_harness.sh`, `thorium_harness.sh`,
  `hosts_guard_harness.sh`. Each sources the core, sources the real
  `scripts/lib/common.sh`, and redefines the helpers that live in the **entry
  script** rather than any lib.

**To add a family:** copy `thorium_harness.sh`'s shape (~124 lines). jscpd
already excludes `**/lib/tests/**`, so shared test setup carries no
duplication risk.

## The loop, per lib

```bash
# 1. write tests/test_<lib>.sh, chmod +x it
# 2. run the suite bare first -- much faster than the jail
bash linux_configuration/scripts/single_use/fixes/lib/tests/run_all.sh

# 3. then measure through the runner, in a detached worktree
timeout 900s bash meta/scripts/shell_coverage_jail.sh --timeout 600s \
  --subject linux_configuration/scripts/single_use/fixes/lib/tests/run_all.sh \
  --measure <lib>.sh --min 1 --fail-on-case-error -- ""

# 4. close the gap, repeat until 100.00%
```

**Always measure through `run_all.sh`, never a single test file.**
**Always pass `--timeout 600s`** — see the timeout section below.

## The bar for taking a lib off the allowlist

1. Measure 100.00% through `run_all.sh`.
2. **Measure again at `--min 100`** so a shortfall is a non-zero exit.
3. Remove the line from `meta/shell-coverage-allowlist.txt`, then run the gate
   with **the line already deleted** and confirm exit 0:
   ```bash
   bash meta/scripts/check_shell_coverage.sh <path to lib>.sh
   # expect: "every checked shell library meets the coverage bar"
   ```
   Running it BEFORE deleting the line proves nothing — it passes via the
   exemption.

## NEW: the case timeout is now the binding constraint on suite size

`meta/scripts/lib/shell_coverage_bar.sh` now passes **`--timeout 600s`** to the
jail. The jail's own default is 120s, and this suite outgrew it: **98s bare**
at 28 test files, and kcov instrumentation roughly doubles that.

The failure mode is nasty and worth recognising instantly: the jail prints a
correct percentage AND a timeout warning, and `--fail-on-case-error` turns that
into a failed gate. It looked like this:

```
warn: case timed out after 120s:
bt_audio.sh: 127/127 lines = 100.00%
Error: 1 case(s) exited non-zero
```

A lib measuring a perfect 100% was failing the gate. If you add enough test
files to approach 600s instrumented, raise it again — the flag is a hang
catcher, not a performance budget. The cost is that a genuine hang now takes
10 minutes per pass to surface.

## NEVER run two coverage jails at once

Every false `FAIL` in the previous session came from CPU contention: two jails,
or a jail plus `bash run_all.sh`, and one of them times out. `bt_pairing.sh`,
`bt_audio.sh` and `bt_report.sh` each "failed" a sweep and then passed solo.

When a sweep is running, do **zero-CPU work only** — write docs, read source.
Do not run the suite, the gate, or another jail.

## NEW: adding a test file can break an ALREADY-CLEARED lib

This is the most important operational lesson of the session, and it is
**unexplained**.

Adding `test_arch_sysctl.sh` to the suite made kcov stop registering
`bt_audio.sh` entirely — "kcov instrumented no lines" — for a lib that is off
the allowlist at 127/127. That turned the gate red on `main`. Bisected:

- `a2b23521` (before) — bt_audio 127/127
- `afe6ac3a` (shfmt reformat) — bt_audio 127/127
- `7c14cfca` (the file lands) — bt_audio "instrumented no lines"

Removing that one file restores 127/127 with every other new test file still
present. Ruled out, each by reverting it alone in a throwaway worktree:
`export out`, the `_t_hide` cache, and **runtime** (it still fails at a 600s
timeout with no timeout warning, so it is NOT the timeout issue above).

**Therefore: after adding any test file to this suite, re-measure an
already-cleared lib, not just your new one.** `bt_audio.sh` is the right canary
— it is the one that broke, it is gated, and it sorts late in the glob.

## The quarantined file

`tests/arch_sysctl_quarantined_cases.sh` holds **23 green assertions** for
`arch_sysctl.sh`. It is deliberately OUTSIDE the `test_*.sh` glob `run_all.sh`
iterates, because of the contagion above. Run it directly:

```bash
bash linux_configuration/scripts/single_use/fixes/lib/tests/arch_sysctl_quarantined_cases.sh
```

`arch_sysctl.sh` stays on the allowlist. It has never measured through the jail
anyway — it reports "instrumented no lines" on its own too, like `nc_php.sh`.
Its header records what to re-verify before un-quarantining it.

## The instrument

Coverage = `(PS4-traced lines | kcov hits) & (kcov line set - continuation lines)`

`continuation_lines()` in `meta/scripts/lib/shell_coverage_lines.py` excludes
lines kcov instruments but bash attributes no statement to:

- continuation lines of a multi-line **quoted** argument;
- **multi-line array literal** elements and the closing paren (`_ARRAY_OPEN`);
- **a closing brace plus an operator** — `} |`, `} >>file` (`_CLOSING_BRACE_OP`);
- **NEW: a loop terminator plus a redirect** — `done >file`, `done <file`,
  `done | cmd` (`_LOOP_END_OP`). bash attributes the redirected compound
  statement to the loop's OPENING line. Reproduced minimally: in a
  three-iteration loop ending `done >"$1"`, the body reports hits=3 and the
  `done` line hits=0. This took `hosts_guard_rollback.sh` 97.01% -> 100%.
  The redirect is REQUIRED by the pattern — a bare `done` stays in the
  denominator, so genuinely uncovered loops are still caught.

Acceptance test if you touch it: `dot_resolver_install.sh` = 39/39 and
`rpi_nc_ca.sh` = 73/73, **through `features/lib/tests/run_all.sh` WITH the
`jail_args` file beside it** (that suite refuses to run bare, and `mapfile` is
bash-only — wrap in `bash -c`). And **no lib's percentage may go DOWN**.

A lib already at 100.00% **cannot** regress from excluding more lines
(`covered_set = (executed|traced) & denominator`). Over-exclusion is the only
real risk. Audit any new predicate by printing every newly-excluded line **with
its text** — and **grep the WHOLE repo, not just `fixes/lib`**. `_LOOP_END_OP`
looked like it touched 2 lines when scoped to `fixes/lib`; repo-wide it touches
~75, of which 14 are in gated non-exempt libs.

### The one known-unfixed artifact

`bt_adapter.sh` sits at **98.55% (68/69), still exempt**, capped by line 97:
the opening line of a backslash-continued **assignment**
(`result=$(dbus-send ... \`). bash attributes that statement to the LAST line
of the run, so the opening line can never be covered.

**The predicate is narrower than "has a backslash".** A backslash-continued
plain **command** (`apply_fix "..." \`) is attributed to its **FIRST** line and
covers normally. Only the assignment flavour caps a lib:

```bash
grep -nE '^[[:space:]]*(local[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=.*\\$' <lib>
```

Across all 22 libs that matches only `bt_adapter.sh` (1) and `bt_audio.sh` (2),
and bt_audio still reached 100%. **Neither remaining lib matches it**, so it
does not block this job.

## Work the jail in a detached worktree

The jail fingerprints `git status --porcelain` and aborts with "a write escaped
the jail" if the tree changes **during** a run — it compares a delta, so a
pre-existing dirty file is fine but any concurrent write is not. **A `git mv`
you have not committed yet also trips it.**

Use a throwaway worktree and **copy one-way, INTO it, never out**:

```bash
SP=/tmp/claude-.../scratchpad
git worktree add --detach "$SP/cov" HEAD
cp <files> "$SP/cov/<same paths>"      # never the reverse
```

Copying _out_ of the worktree is how an earlier session silently reverted its
own uncommitted harness edit, twice.

## Production bugs keep turning up. Expect more.

Three so far, all dead branches no test could cover without noticing:

- `bt_audio.sh:21` — `timeout 3 _run_as_user wpctl status`. `timeout` is a
  binary and cannot invoke a shell function, so it always returned 127.
- `arch_perf_report.sh:36,65` — journal-size regex required a space before the
  unit (`4.2 G`), but `journalctl` prints `305.5M`.
- `arch_hardware.sh` — **the same regex bug again**, found this session. The
  vacuum was unreachable; a multi-gigabyte journal would never be trimmed.

**When a branch looks untestable, check whether it is actually reachable in
production before writing a test around it.** The user's standing answer is
"fix it in this commit".

## Traps that cost real time

- **`shfmt` runs on every staged shell file and WILL reformat your lib**,
  moving the denominator and invalidating a measurement taken minutes earlier.
  Run `shfmt -l <libs>` FIRST and land any reformat as its own commit.
- **The 250-line cap aborts the commit**, and a task notification can report
  "completed (exit code 0)" for a commit that actually failed. Every test file
  for a lib this size has needed splitting into two. `lib_test_core.sh` is at
  240 — the next helper added there forces a split.
- **A stub must consume what the real tool consumes.** A `bluetoothctl` stub
  that read one line and exited closed the pipe, so the writing block took
  SIGPIPE partway through.
- **`_t_stub` already records the invocation** into `$DEV/calls`. A custom body
  that also records double-counts every call.
- **Check the argument position before writing a stub.** `pacman -Qi <pkg>`
  puts the package in `$2`, not `$3`; two assertions passed for the wrong
  reason until that was fixed.
- **A function that appends to a global array must not be called inside `$( )`.**
- **A top-level stub function SHADOWS the subject's own** for every later
  assertion. Put redefinitions in a subshell, and bind them with
  `eval '_real_name() { _my_recorder "$@"; }'` so shellcheck still sees the
  recorder as called (SC2329).
- **Do not `pgrep -f <thing>` in a wait loop** — the loop's own command line
  matches, so it never exits. It also makes `pgrep -c` report a phantom match.
- **`--fail-on-case-error` or you are flying blind.** The jail suppresses the
  suite's stdout, so assertions fail invisibly without it.
- **Do not pipe jail output through `grep 'lines ='`** — that filter hides the
  `warn: case timed out` line, which is exactly the diagnosis you need.
- **`mapfile` is bash-only**; the Bash tool's shell is zsh. Wrap in `bash -c`.
- **`git stash` is blocked by a hook** — even a bare `git stash list` inside a
  compound command trips the guard. Use a detached worktree.
- **Stage narrowly.** A `git add` of a directory swept another agent's
  untracked file into a commit and broke the push on a prettier check.
- **Commits exceed a 2-minute foreground timeout.** Background them and
  **check the result**.
- **Two-strike rule.** Two failed attempts at the same thing -> stop, document,
  keep the working state.

## Rules that will bite you

- **No suppressions, ever.** Fix SC2016/SC2034/SC2329/C901 at the source. When
  three arrays in `hosts_guard_harness.sh` tripped SC2034 because only the
  libs read them, the fix was a `_t_table` helper the tests actually call —
  bash cannot export an array.
- **Never weaken an assertion to move a number.** One asserted
  `_t_lacks ... "hosts-guard.path="` against a line reading
  `hosts-guard.path=absent`; the fix was `grep -c '=$'`, not deletion.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (validate with
  `python3 meta/scripts/validate_evidence.py <file>`), **plus a contract** in
  `docs/superpowers/contracts/` once **>=4 code files** are staged. `.sh`
  counts; so does the allowlist.
- **Put the MEASURED number in it**, never a rounded or hoped-for one. A
  `"result": "fail"` entry is legitimate and `validate_evidence.py` accepts it.
- **New test files need the exec bit** — `chmod +x` the working tree.
- Work directly on `main`. Branch creation is blocked.

## Seams: what each remaining lib needs

Neither lib can be tested without redirecting its writes. The established
idiom is an override **defaulting to the real path**, so production behaviour
is byte-identical:

```bash
local dropin="${SYSCTL_DROPIN_DIR:-/etc/sysctl.d}/99-performance-tuning.conf"
```

Reuse the names already in use elsewhere rather than inventing parallel ones:
`SYSTEMD_UNIT_DIR`, `JOURNALD_CONF_DIR`, `UDEV_RULES_DIR`, `SYSCTL_DROPIN_DIR`.
Grep the entry script for a name before picking it — a collision is silent.

- **`ubuntu_perf_fixes.sh`** (4 seams): `/etc/sysctl.d/99-performance-tuning.conf`,
  `/etc/systemd/system/nvidia-persistence.service`,
  `/etc/systemd/system/nvidia-persistence-mode.service`, `/etc/default/earlyoom`.
  At 215 lines, check `wc -l` after patching — seam comments run 3-4 lines each.
- **`nvidia_config.sh`** (3+ seams): `XORG_CONF`, `XORG_CONF_D`, `PROFILE_FILE`
  (`/etc/profile`). **Check whether these are `local` or plain globals** — if
  they are assigned inside a function, a harness `export` will not survive the
  assignment and they still need the `${VAR:-default}` form.

Verify containment after the first run: `ls -la` the real paths and confirm
the mtimes did not change.

## PRE-EXISTING: ~12 gated libs OUTSIDE fixes/lib already fail the gate

`check_shell_coverage.sh` is **not wired into pre-commit**, so a lib can sit
below the bar indefinitely without anything going red. Measured this session,
and confirmed by re-running at an earlier commit that these are **not** caused
by the `_LOOP_END_OP` instrument change:

```
lib/common_packages.sh                                   FAIL (pre-existing)
periodic_background/digital_wellbeing/lib/ms_override_mgr.sh   FAIL
periodic_background/digital_wellbeing/lib/ms_scripts.sh        FAIL
periodic_background/lib/periodic_browser.sh              FAIL (pre-existing)
single_use/utils/lib/analyze_repo_symbols.sh             FAIL
single_use/utils/lib/bl9000_backup.sh                    FAIL
single_use/utils/lib/download_media.sh                   FAIL
single_use/utils/lib/idle_inhibit.sh                     FAIL
single_use/utils/lib/offline_index.sh                    FAIL
single_use/utils/lib/steam_api.sh                        FAIL (pre-existing)
single_use/utils/lib/steam_report.sh                     FAIL
```

`hosts_protect_custom.sh` and `hosts_protect_unblock.sh` PASS.

This is a separate, larger job than the `fixes/lib` campaign — `utils/lib/`
alone is most of it. **Do not fold it into this task without asking**; it is
listed here so the next session recognises these as known and pre-existing
rather than something it just broke.

## Finish with a serial sweep

Once both libs are committed, run **one** sweep over every off-allowlist lib in
`fixes/lib`, serially, with nothing else running:

```bash
for lib in bt_report bt_pairing bt_audio arch_perf_report arch_perf_probes \
           arch_perf_fixes ubuntu_perf_more arch_cpu arch_hardware \
           thorium_repairs hosts_guard_migrate hosts_guard_rollback \
           ubuntu_perf_fixes nvidia_config; do
  printf '%-24s ' "$lib.sh"
  timeout 900 bash meta/scripts/check_shell_coverage.sh \
    "linux_configuration/scripts/single_use/fixes/lib/$lib.sh" \
    >/dev/null 2>&1 && echo PASS || echo "*** FAIL ***"
done
```

At ~2 min/lib that is ~30 minutes. Background it and poll the log, but do not
fill the gap with anything that forks.

## State as of 2026-08-23

Allowlist **86**, down from 91. The `fixes/lib/tests` suite is 28 test files
plus 6 harnesses and the core, ~470 assertions, all green, all shellcheck-clean
with zero suppressions. Suite runtime **98s bare**.

Still exempt and measured by an earlier session, **all predate the instrument
fixes and may now measure higher — re-measure before writing a single test**:
`dwm_config.sh` 98.48%, `pacman_hook_stall_setup.sh` 96.30%,
`aw_autostart.sh` 97.56%, `rpi_nc_install.sh` 96.59%,
`transcribe_pkgmgr.sh` 98.00%, `clean_audio_filters.sh` 91.40%,
`transcribe_deps.sh` 92.31%.

`rpi_nc_ca.sh` (73/73) and `dot_resolver_install.sh` (39/39) are at 100% and
could come off the allowlist whenever you want, by the three-step bar.

`nc_php.sh` does not measure at all — "kcov instrumented no lines", on every
version of the instrument. Same bucket as `arch_sysctl.sh`; treat as unverified.

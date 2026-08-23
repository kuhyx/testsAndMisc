# STATUS 2026-08-23 (later session): jobs 1 and 2 are DONE

> Read this box before anything below it. The rest of this file is the
> ORIGINAL handoff, kept because its kcov/jail notes are still the reference
> for measuring a lib on purpose. Its SCOPE is now obsolete.

**Job 1 — the push gate — DONE (commit 8ab15446).** ~130s to:
docs-only 7.6s, python 25.3s, one shell suite 43.6s, unchanged-tree re-push
0.005s. The guarantee is intact; a broken python assertion and a broken shell
assertion were each refused with exit 1.

Found while measuring it: `ci_mirror.sh` called `pytest_changed_packages.py`
with no arguments, and that script returns 0 on empty argv. **The pre-push
python stage had never run a single test.** Behind it sat a real failing test
(fixed in ff3ea99a).

**Job 2 — the 100% shell bar — DELIBERATELY DROPPED (commit 578c4a6c).**
The user's call on 2026-08-23, after being shown the real cost. The bar had
been raised from a presence check only the day before (bca70b67), and pricing
it out honestly: one hand-written test file per lib (fixes/lib took 34 files
for 22 libs), a serial jail at 37-90s a pass, and a production seam needed in
most libs before they are testable at all — several days for a repo of
personal automation scripts. `is_covered` is a presence check again.

**The ratchet is now WIRED into pre-commit (commit 46c8f065)** — it never was
before, which is why it rotted. 0 BLOCK entries, 0.16s repo-wide. The three
`meta/scripts/lib` coverage-tooling libs got a 48-assertion suite so they stop
blocking it.

**Python needs nothing:** 2101 tests, 100.00%, zero missing statements or
branches, measured in a clean worktree. **File-length cap needs nothing:** 0
violations, hook-enforced.

**What is left, if anyone wants it:** 8 directories still have no suite at all
(`.githooks/lib`, `scripts/meta/lib`, `mtk_root/lib`, `digital_wellbeing/{pacman,
virtualbox}/lib`, `system-maintenance/bin/lib`, `single_use/{fresh-install,}/lib`)
— 20 libs, ~1,980 lines. All are allowlisted, so nothing is blocked. This is
optional work now, not a campaign.

**Traps worth carrying forward, beyond the list below:**

- **Never `git reset --hard` to undo a probe commit.** It discards UNSTAGED
  working-tree edits. That cost a full rewrite of `ci_mirror.sh` this session.
  Recovery: pre-commit stashes unstaged files to `~/.cache/pre-commit/patch*`;
  `git apply` on the newest one restored it exactly. Use
  `git revert --no-commit <sha>`.
- **Read the predicate, not the header comment.** `check_shell_coverage.sh`'s
  header still described a presence gate for a full day after the gate became
  a 100% bar. Acting on the prose produced a confidently wrong scope estimate.
- A sourced-only lib takes `# shellcheck shell=bash`, no shebang, no exec bit,
  or `check-shebang-scripts-are-executable` fails the commit.

---

# Next session: make the push gate fast, then close the coverage holes

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

There are **two jobs** here. Do them in order — job 1 is small and makes job 2
bearable, because job 2 involves many commits.

---

# JOB 1: get `git push` under 10 seconds

## What is slow

`git push` currently takes **~130 seconds**. Nearly all of it is the
`ci-mirror` pre-push hook (`meta/scripts/ci_mirror.sh`), which deliberately
re-runs CI locally so a red push cannot reach GitHub. It does four things
inside a fresh `git worktree` checkout of HEAD:

| stage                                     | what it costs                         |
| ----------------------------------------- | ------------------------------------- |
| venv install from `requirements.txt`      | ~0s when cached, ~40s on a change     |
| `pre-commit run --all-files`              | the bulk of it                        |
| `pytest_changed_packages.py` in that venv | seconds to minutes, package-dependent |
| `run_shell_test_gate` (the shell suites)  | ~40s+                                 |

For comparison: **pre-commit is already fast — 4.8s measured.** Do not touch
it. The whole problem is pre-push.

## The target, and the honest tradeoff

The user asked for **under 10 seconds, ideally ~10s or less, total**.

**Be straight with them about this:** a clean-venv install plus `--all-files`
plus two test suites cannot fit in 10s. Something must actually be given up.
The decision is theirs, so **measure first, then present the options and their
real costs, then implement the one they pick.**

### Step 1 — measure each stage separately

Do this before proposing anything. Numbers, not guesses:

```bash
cd /home/kuhy/testsAndMisc
SP=$(mktemp -d); git worktree add --detach --quiet "$SP/co" HEAD

time (cd "$SP/co" && SKIP=pytest-coverage pre-commit run --all-files)
time (cd "$SP/co" && python meta/scripts/pytest_changed_packages.py)
time bash linux_configuration/scripts/single_use/fixes/lib/tests/run_all.sh

git worktree remove --force "$SP/co"
```

Then find which individual pre-commit hooks dominate `--all-files`:

```bash
cd "$SP/co" && for h in $(grep -oP '(?<=id: ).*' .pre-commit-config.yaml | sort -u); do
  s=$(date +%s%N); SKIP='' pre-commit run "$h" --all-files >/dev/null 2>&1
  printf '%6d ms  %s\n' $(( ($(date +%s%N)-s)/1000000 )) "$h"
done | sort -rn | head -15
```

### Step 2 — the options, in the order I would try them

1. **Only check what changed.** The single biggest win and the least loss.
   `--all-files` is the expensive part; `pre-commit run --from-ref
origin/main --to-ref HEAD` checks the pushed range instead. The clean
   worktree already guarantees you are checking committed content.
   Similarly, only run a shell suite when the push touches shell files.
2. **Parallelise the stages.** `pre-commit --all-files`, pytest and the shell
   gate are independent. Run them concurrently and wait. Roughly the cost of
   the slowest rather than the sum. **Note:** two coverage jails must never run
   at once (see the warning in job 2), so if the shell gate is jailed, keep it
   serial with respect to any other jail.
3. **Cache on tree state.** Skip the whole mirror when
   `git rev-parse HEAD:` (the tree hash) matches the last green run, recorded
   in a dotfile. A re-push of an unchanged tree then costs ~0s.
4. **Move ci-mirror off pre-push entirely.** Pre-push drops to ~5s. The cost
   is real and must be stated plainly: **a red push can then reach GitHub**,
   and CI catches it minutes later instead of the hook catching it instantly.
   The repo's `refuse-red-ci` hook already blocks the NEXT commit on a red
   baseline, so this is less dangerous than it sounds — but it is a genuine
   change in guarantees, not a free win.

Options 1-3 are optimisations that keep the guarantee. Option 4 trades the
guarantee for speed. **1+2+3 together may well reach ~10s; try them before
proposing 4.** If they land at, say, 25s, say so honestly rather than reaching
for 4 without asking.

### Step 3 — prove it

```bash
time git push        # the number that matters
```

And prove the gate still catches things: deliberately break something
(a failing assertion in a shell test), confirm the push is refused, then
revert. A fast gate that no longer gates is worse than a slow one.

## Do not

- Do not weaken or delete a test to make a gate faster.
- Do not add `--no-verify` anywhere, or suggest it. It is forbidden by the
  user's rules.
- Do not touch pre-commit's 4.8s — it is already at target.

---

# JOB 2: actually get the repo to 100% coverage

The user asked to "make the repo truly 100% test covered". Be careful with
that phrasing: **it is a large campaign, not one task.** Scope it, report the
real size, and then work through it. Do not report it done until it is.

## Where things actually stand

### Shell: `meta/shell-coverage-allowlist.txt` has **84 exempt libs**

```bash
grep -vc '^#' meta/shell-coverage-allowlist.txt     # 84
```

Each line is a shell library allowed to sit below 100% line coverage. The
just-finished campaign took this from 91 to 84 by clearing seven libs in
`fixes/lib`. The remaining 84 are the job.

### ~12 gated libs OUTSIDE `fixes/lib` fail the gate RIGHT NOW

`check_shell_coverage.sh` is **not wired into pre-commit**, so these have been
failing silently. Confirmed pre-existing (verified against an earlier commit —
they are not caused by recent work):

```
lib/common_packages.sh                                        FAIL
periodic_background/digital_wellbeing/lib/ms_override_mgr.sh  FAIL
periodic_background/digital_wellbeing/lib/ms_scripts.sh       FAIL
periodic_background/lib/periodic_browser.sh                   FAIL
single_use/utils/lib/analyze_repo_symbols.sh                  FAIL
single_use/utils/lib/bl9000_backup.sh                         FAIL
single_use/utils/lib/download_media.sh                        FAIL
single_use/utils/lib/idle_inhibit.sh                          FAIL
single_use/utils/lib/offline_index.sh                         FAIL
single_use/utils/lib/steam_api.sh                             FAIL
single_use/utils/lib/steam_report.sh                          FAIL
```

`hosts_protect_custom.sh` and `hosts_protect_unblock.sh` PASS.

**Start here.** These are worse than an exemption: they are libs the gate
believes it is checking and which do not meet the bar. `single_use/utils/lib/`
is most of the list and shares one `tests/` directory, so one harness covers
several.

### Python: `python_pkg/` is 25 packages at `fail_under = 100`

Branch coverage is already enforced at 100% by `meta/pyproject.toml`, so this
is likely in decent shape. **Verify before assuming** — and note the user's
standing rule: never exclude a package from coverage, write the tests.

```bash
timeout 1800 python -m pytest python_pkg --cov=python_pkg --cov-report=term-missing -q 2>&1 | tail -30
```

### Other languages

`billsplit/` (Dart), `reverse_survivors/`, `poker-stakes/` (TS) have their own
CI. Check their gates before claiming anything about them.

## Report the real scope first

Before writing a single test, produce a count: N shell libs exempt, M gated
libs failing, Python status, other languages. Give the user that number and a
suggested order. "100% covered" spans several days of work; they should see
the shape before you spend it.

## The order I would work in

1. The ~12 gated-but-failing shell libs (worst: the gate is lying today).
2. Wire `check_shell_coverage.sh` into pre-commit so it cannot rot again —
   **but only after 1**, or every commit is blocked. Mind job 1: this hook is
   jailed and slow, so scope it to changed files.
3. The 84 allowlist entries, cheapest first.
4. Python, if the run above shows gaps.

---

# How to do shell coverage work here (read before starting job 2)

## The suite and its harnesses

`linux_configuration/scripts/single_use/fixes/lib/tests/` is the reference
suite: **30 test files, 645 assertions, all green, zero suppressions, 37s.**
Copy its shape. Layers:

- `run_all.sh` — the runner, and the subject the gate measures through.
- `lib_test_core.sh` (194 lines) — assertions and stubs.
- `lib_test_path.sh` (67 lines) — `_t_hide` and the PATH shim farm.
- Six family harnesses, one per entry script.

Key primitives:

- `_t_eq` / `_t_contains` / `_t_lacks`
- `_t_stub NAME BODY`, plus `_t_stub_stdin` (quoted heredoc), `_t_stub_cat`,
  `_t_stub_writes`. Use these rather than `_t_stub foo '...$1...'`, which
  trips SC2016 every time.
- **`_t_run FUNC [ARG...]`** — runs FUNC in the CURRENT shell, output in
  `$out`. **Never `out="$(func)"`:** command substitution forks a subshell and
  kcov then does not register the sourced lib at all (measured: 0 lines via
  `$( )`, 54 via a direct call).
- **`_t_hide TOOL...`** — makes a tool genuinely unfindable. It KEEPS
  `$FAKE_BIN` on PATH, so **`_t_unstub` the tool first** or the harness's own
  default stub still satisfies `has_cmd` and the branch never runs.
- `_t_unstub` (runs `hash -r`; deleting the file alone does nothing).

## Production seams

Most libs write to `/etc`. The idiom is an override **defaulting to the real
path**, so production behaviour is byte-identical:

```bash
local dropin="${SYSCTL_DROPIN_DIR:-/etc/sysctl.d}/99-performance-tuning.conf"
```

Reuse existing names — `SYSTEMD_UNIT_DIR`, `JOURNALD_CONF_DIR`,
`UDEV_RULES_DIR`, `SYSCTL_DROPIN_DIR` — and grep the entry script before
picking one; a collision is silent.

**Watch for globals ASSIGNED inside a function** (`XORG_CONF="/etc/..."` with
no `local`). Exporting from the harness does not survive the assignment; the
default must live at the assignment itself.

After the first run, `ls -la` the real paths and confirm the mtimes did not
move.

## The measurement loop

```bash
# 1. write the tests, chmod +x
# 2. run bare first -- far faster than the jail
bash <suite>/run_all.sh

# 3. measure through the RUNNER, in a detached worktree
timeout 900s bash meta/scripts/shell_coverage_jail.sh --timeout 600s \
  --subject <suite>/run_all.sh --measure <lib>.sh --min 1 \
  --fail-on-case-error -- ""
```

Then the three-step bar to clear an exemption:

1. 100.00% through `run_all.sh`.
2. Again at `--min 100`, so a shortfall is a non-zero exit.
3. Delete the allowlist line, **then** run
   `bash meta/scripts/check_shell_coverage.sh <lib>` and confirm exit 0.
   Running it before deleting proves nothing — it passes via the exemption.

## Traps that cost real hours last session

- **Verify an edit landed.** A seam edit reported success, was measured, and
  never reached the commit; ci-mirror caught it only because it runs from a
  clean checkout. **After editing, `grep` the file for what you just wrote.**
- **Run the suite from a clean checkout before pushing.** It catches exactly
  the above:
  ```bash
  SP=$(mktemp -d); git worktree add --detach "$SP/c" HEAD
  bash "$SP/c/<suite>/run_all.sh"; git worktree remove --force "$SP/c"
  ```
- **NEVER run two coverage jails at once.** Every false FAIL last session was
  CPU contention — a jail plus another jail, or a jail plus `run_all.sh`.
  Libs "failed" a sweep and passed solo. While a sweep runs, do zero-CPU work.
- **Another agent may be committing to this repo concurrently.** The jail
  fingerprints `git status --porcelain` and aborts with "a write escaped the
  jail" on THEIR edits. Measure in a detached worktree, and re-check a
  transient gate failure before believing it.
- **Adding a test file can break an ALREADY-CLEARED lib.** Unexplained:
  `test_arch_sysctl.sh` made kcov stop registering `bt_audio.sh` entirely
  ("instrumented no lines"), turning the gate red. Ruled out: `export out`,
  the `_t_hide` cache, and runtime (still fails at a 600s timeout). The file
  is quarantined as `arch_sysctl_quarantined_cases.sh`, outside the
  `test_*.sh` glob, with 23 still-green assertions.
  **After adding any test file, re-measure an already-cleared lib** —
  `bt_audio.sh` is the canary.
- **`shfmt` reformats staged shell files**, moving the denominator and
  invalidating a measurement. Run `shfmt -l` first and land reformats
  separately.
- **The 250-line cap aborts commits**, and a task notification can report
  "completed (exit code 0)" for a commit that actually failed. Check.
- **Stage narrowly.** A `git add` of a directory swept another agent's
  untracked file into a commit and broke the push.
- **`mapfile` is bash-only**; the tool shell is zsh. Wrap in `bash -c`.
- **`git stash` is blocked** — even `git stash list` inside a compound
  command trips the guard. Use a detached worktree.
- **Do not pipe jail output through `grep 'lines ='`** — that hides the
  `warn: case timed out` line, which is the diagnosis you need.
- **Do not `pgrep -f <thing>` in a wait loop** — the loop's own command line
  matches, so it never exits.

## The coverage instrument

`coverage = (PS4-traced | kcov hits) & (kcov line set - continuation lines)`

`continuation_lines()` in `meta/scripts/lib/shell_coverage_lines.py` excludes
lines kcov instruments but bash attributes no statement to: multi-line quoted
arguments, multi-line array literals, `} |` / `} >>file`, and (added last
session) `done >file` / `done <file`.

If you touch it: the acceptance pair is `dot_resolver_install.sh` = 39/39 and
`rpi_nc_ca.sh` = 73/73 through `features/lib/tests/run_all.sh` **with its
`jail_args` file**. And audit any new predicate by printing every newly
excluded line **with its text, across the WHOLE repo** — scoping that audit to
one directory last session undercounted the blast radius by 35x (2 lines vs
~75).

A lib already at 100% cannot regress from excluding more lines. Over-exclusion
is the only real risk.

### Known-unfixed artifact

`bt_adapter.sh` is capped at 98.55% (68/69) by line 97: the opening line of a
backslash-continued **assignment**, which bash attributes to the LAST line of
the run. A backslash-continued plain **command** is attributed to its first
line and covers normally. Find them with:

```bash
grep -nE '^[[:space:]]*(local[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=.*\\$' <lib>
```

### Libs that do not measure at all

`arch_sysctl.sh` and `nc_php.sh` both report "kcov instrumented no lines" on
every version of the instrument. Treat as unverified; they stay exempt.

---

## State as of 2026-08-23

- Allowlist **84** (was 91 at the start of the previous session).
- `fixes/lib` cleared: `arch_cpu` 57/57, `arch_hardware` 94/94,
  `thorium_repairs` 75/75, `hosts_guard_migrate` 81/81,
  `hosts_guard_rollback` 65/65, `ubuntu_perf_fixes` 81/81,
  `nvidia_config` 76/76.
- The `fixes/lib` suite: 30 files, 645 assertions, 37s, zero suppressions.
- Three production bugs were found by writing tests, all dead branches:
  `bt_audio.sh:21` (`timeout` cannot invoke a shell function),
  `arch_perf_report.sh:36,65` and `arch_hardware.sh` (journal-size regex
  demanded a space before the unit, but `journalctl` prints `305.5M`, so the
  vacuum was unreachable). **Expect more. When a branch looks untestable,
  check whether it is reachable in production first** — the user's standing
  answer is "fix it in this commit".

Still exempt and measured by an older session; **all predate the instrument
fixes and may now measure higher — re-measure before writing any test**:
`dwm_config.sh` 98.48%, `pacman_hook_stall_setup.sh` 96.30%,
`aw_autostart.sh` 97.56%, `rpi_nc_install.sh` 96.59%,
`transcribe_pkgmgr.sh` 98.00%, `clean_audio_filters.sh` 91.40%,
`transcribe_deps.sh` 92.31%.

`rpi_nc_ca.sh` (73/73) and `dot_resolver_install.sh` (39/39) are already at
100% and can come off the allowlist whenever you want, by the three-step bar.
That is two free entries.

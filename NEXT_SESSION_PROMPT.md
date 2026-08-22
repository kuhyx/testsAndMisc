# Next session: the 8 remaining untested `fixes/lib` libs

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The job

`linux_configuration/scripts/single_use/fixes/lib/` has 22 libs. **Eight still
have no tests.** Write them, to 100% line coverage, and take each one off
`meta/shell-coverage-allowlist.txt`.

| lines | lib                       | entry script                          |
| ----- | ------------------------- | ------------------------------------- |
| 215   | `ubuntu_perf_fixes.sh`    | `fix_ubuntu_performance.sh`           |
| 202   | `arch_hardware.sh`        | `optimize_arch_desktop.sh`            |
| 180   | `nvidia_config.sh`        | `nvidia_troubleshoot.sh`              |
| 179   | `thorium_repairs.sh`      | `fix_thorium.sh`                      |
| 161   | `hosts_guard_migrate.sh`  | `migrate_hosts_guard_to_guard_lib.sh` |
| 141   | `hosts_guard_rollback.sh` | same                                  |
| 126   | `arch_cpu.sh`             | `optimize_arch_desktop.sh`            |
| 122   | `arch_sysctl.sh`          | `optimize_arch_desktop.sh`            |

**Suggested order: smallest first, grouped by entry script.** The three
`optimize_arch_desktop.sh` libs (`arch_cpu`, `arch_sysctl`, `arch_hardware`)
share a harness; so do the two hosts-guard libs and the two ubuntu-perf ones.

**The last handoff mis-grouped these — do not trust its "arch perf six share
one entry script" claim.** They span four different entry scripts, as above.

## Everything you need already exists — do NOT build a new harness

`fixes/lib/tests/` is a working suite: **20 test files, all green, all
shellcheck-clean with zero suppressions.** It has three layers:

- `run_all.sh` — the runner. **This is the subject the gate measures through.**
- `lib_test_core.sh` — the shared primitives. Read this first:
  - `_t_eq` / `_t_contains` / `_t_lacks` / `_t_pass` / `_t_fail`
  - `_t_stub NAME BODY`, and the three helpers that exist to keep call sites
    free of quoted `$`: **`_t_stub_stdin NAME` (body from a quoted heredoc),
    `_t_stub_cat NAME FIXTURE` (print `$DEV/FIXTURE`), `_t_stub_writes NAME
ARGNUM CONTENT`**. Use these instead of `_t_stub foo '...$1...'`, which
    trips SC2016 every single time.
  - `_t_unstub NAME...` (runs `hash -r`; deleting the file alone does not work)
  - **`_t_hide TOOL...`** — rebuilds PATH from symlinks to every real binary
    EXCEPT the named ones. This is how you test a "not installed" branch when
    the host genuinely has the tool. Do NOT drop PATH to `$FAKE_BIN` alone:
    that also hides `grep`/`head`/`awk`, and the case then passes for the
    wrong reason.
  - `_t_calls` / `_t_reset_calls` — what the stubs recorded.
- Two family harnesses, `bt_harness.sh` and `arch_perf_harness.sh`. Each
  sources the core, sources the real `scripts/lib/common.sh` for the
  production `log_*`/`has_cmd` helpers (it is inert at source time), and
  redefines the helpers that live in the **entry script** rather than any lib.

**To add a family:** copy `arch_perf_harness.sh`'s shape. It is ~100 lines and
the only family-specific parts are the entry-script helpers and the default
stub list. jscpd already excludes `**/lib/tests/**`, so shared test setup
carries no duplication risk.

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

**Always measure through `run_all.sh`, never a single test file.**

## The bar for taking a lib off the allowlist

1. Measure 100.00% through `run_all.sh`.
2. **Measure again at `--min 100`** so a shortfall is a non-zero exit.
3. Remove the line from `meta/shell-coverage-allowlist.txt`, then run the gate
   with no exemption and confirm exit 0:
   ```bash
   bash meta/scripts/check_shell_coverage.sh <path to lib>.sh
   # expect: "every checked shell library meets the coverage bar"
   ```

Allowlist is at **91** entries — count with `grep -vc '^#'`, since the file
also holds 13 comment lines.

## Work the jail in a detached worktree

The jail fingerprints `git status --porcelain` and aborts with "a write
escaped the jail" if the tree changes **during** a run — it compares a delta,
so a pre-existing dirty file is fine but any concurrent write is not. Editing
anything mid-run trips it, and so does a background build.

Use a throwaway worktree and **copy one-way, INTO it, never out**:

```bash
SP=/tmp/claude-.../scratchpad          # your scratchpad
git worktree add --detach "$SP/cov" HEAD
cp <files> "$SP/cov/<same paths>"      # never the reverse
```

Copying _out_ of the worktree is how the last session silently reverted its
own uncommitted harness edit, twice, and misdiagnosed it as another agent.

## The instrument: FIXED, and now correct for two more shapes

Coverage = `(PS4-traced lines | kcov hits) & (kcov line set - continuation lines)`

`continuation_lines()` in `meta/scripts/lib/shell_coverage_lines.py` excludes
lines kcov instruments but bash attributes no statement to. It now handles:

- continuation lines of a multi-line **quoted** argument (pre-existing);
- **multi-line array literal elements and the closing paren** — bash reports
  the whole assignment at its OPENING line. This alone took
  `arch_perf_fixes.sh` 93.48% -> 100%, and it matters for the libs left:
  `thorium_repairs.sh` has four such arrays and `ubuntu_perf_fixes.sh` one.
- **a closing brace plus an operator** — `} |`, `} >>file` (added in
  `d989cd7e`). This alone took `bt_audio.sh` 96.97% -> 100% and
  `arch_perf_report.sh` 98.33% -> 100%.

Acceptance test if you ever touch it: `dot_resolver_install.sh` = 39/39 and
`rpi_nc_ca.sh` = 73/73, **through `features/lib/tests/run_all.sh` WITH the
`jail_args` file beside it** (that suite refuses to run bare). And **no lib's
percentage may go DOWN**.

Note the arithmetic that bounds any denominator change: `_measure` computes
`covered_set = (executed|traced) & denominator`, so a lib already at 100.00%
**cannot** regress from excluding more lines. Over-exclusion is the only real
risk — it inflates coverage and could promote an untested lib — so audit any
new predicate by printing every newly-excluded line **with its text**.

### The one known-unfixed artifact

`bt_adapter.sh` sits at **98.55% (68/69), still exempt**, capped by line 97:
the opening line of a backslash-continued **assignment**
(`result=$(dbus-send ... \`). bash attributes that statement to the LAST line
of the run, so the opening line can never be covered.

**The predicate is narrower than "has a backslash".** A backslash-continued
plain **command** (`apply_fix "..." \`) is attributed to its **FIRST** line and
covers normally — `bt_pairing.sh` has three and reached 100%. Only the
assignment flavour caps a lib. Find them with:

```bash
grep -nE '^[[:space:]]*(local[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=.*\\$' <lib>
```

Across all 22 libs that matches only `bt_adapter.sh` (1) and `bt_audio.sh` (2),
and bt_audio still reached 100%, so this blocks exactly one line in one lib.
Fixing it means teaching `continuation_lines()` the command-vs-assignment
distinction. Not worth it for one entry unless you hit it again.

## Two production bugs were found by writing tests. Expect more.

Both were dead branches that no test could have covered without noticing:

- `bt_audio.sh:21` — `timeout 3 _run_as_user wpctl status`. `timeout` is a
  binary and cannot invoke a shell function, so it always returned 127 and
  the PipeWire health check restarted a healthy audio stack on every run.
- `arch_perf_report.sh:36,65` — the journal-size regex required a space
  before the unit (`4.2 G`), but `journalctl` prints `305.5M`. The size
  check and the vacuum were both unreachable.

**When a branch looks untestable, check whether it is actually reachable in
production before writing a test around it.** The user's standing answer when
asked has been "fix it in this commit".

## Traps that cost real time

- **`shfmt` runs on every staged shell file and WILL reformat your lib.** It
  rewrote `bt_audio.sh`'s `{ ...; } \` one-liners into multi-line blocks,
  which raised its denominator 99 -> 132 and invalidated a 100% measurement
  taken minutes earlier. **Re-measure after pre-commit reformats anything**,
  and put the post-format number in the evidence.
- **`bt_audio.sh` is now exactly 250 lines, AT the cap.** The next edit to it
  needs a file split, not a comment trim.
- **A stub must consume what the real tool consumes.** A `bluetoothctl` stub
  that read one line and exited closed the pipe, so the writing
  `{ ...; } | bluetoothctl` block took SIGPIPE partway through and its later
  lines never ran. `cat >/dev/null` before exiting was worth 6 points.
- **A function that appends to a global array must not be called inside
  `$( )`.** The subshell dies with the substitution and the array is empty.
  Redirect to a file and `cat` it instead.
- **A top-level stub function SHADOWS the subject's own** for every later
  assertion. Put redefinitions in a subshell, and bind them with
  `eval '_real_name() { _my_recorder "$@"; }'` so shellcheck still sees the
  recorder as called (SC2329).
- **A prepended stub dir cannot hide a real binary** — use `_t_hide`.
- **Do not `pgrep -f shell_coverage_jail` in a wait loop** — the loop's own
  command line matches, so it never exits.
- **`--fail-on-case-error` or you are flying blind.** The jail suppresses the
  suite's stdout, so assertions fail invisibly without it.
- **Commits exceed a 2-minute foreground timeout.** Background them, and
  **check the result** — a `file-length-cap` failure aborted one commit that
  a task notification had reported as "completed (exit code 0)".
- **`mapfile` is bash-only**; the Bash tool's shell is zsh. Wrap in `bash -c`.
- **Two-strike rule.** Two failed attempts at the same thing -> stop, document,
  keep the working state.

## Rules that will bite you

- **No suppressions, ever.** Fix SC2016/SC2034/SC2329/C901 at the source. The
  three `_t_stub_*` helpers and `_quote_after()` exist precisely because the
  alternative was a `# shellcheck disable`.
- **Never weaken an assertion to move a number.**
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (validate with
  `python3 meta/scripts/validate_evidence.py <file>`), **plus a contract** in
  `docs/superpowers/contracts/` once **>=4 code files** are staged.
- **Put the MEASURED number in it**, never a rounded or hoped-for one.
- **New test files need the exec bit** — `chmod +x` the working tree.
- **Stage narrowly.**
- Work directly on `main`. `git stash` and branch creation are blocked.

## State as of 2026-08-22 (end of session)

Allowlist **91**, down from 98 — seven libs cleared. Fourteen commits,
`4cfc3fdd`..`28f2925c`. The `fixes/lib/tests` suite is 22 files / ~330
assertions, all green, all shellcheck-clean with zero suppressions.

| lib                   | coverage              | status                     |
| --------------------- | --------------------- | -------------------------- |
| `bt_report.sh`        | **37/37 = 100.00%**   | CLEARED                    |
| `bt_pairing.sh`       | **65/65 = 100.00%**   | CLEARED                    |
| `bt_audio.sh`         | **127/127 = 100.00%** | CLEARED                    |
| `arch_perf_report.sh` | **59/59 = 100.00%**   | CLEARED                    |
| `arch_perf_probes.sh` | **93/93 = 100.00%**   | CLEARED                    |
| `ubuntu_perf_more.sh` | **32/32 = 100.00%**   | CLEARED                    |
| `arch_perf_fixes.sh`  | **43/43 = 100.00%**   | CLEARED                    |
| `bt_adapter.sh`       | 68/69 = 98.55%        | exempt, see artifact above |

Measured by an earlier session, all still exempt: `dwm_config.sh` 98.48%,
`pacman_hook_stall_setup.sh` 96.30%, `aw_autostart.sh` 97.56%,
`rpi_nc_install.sh` 96.59%, `transcribe_pkgmgr.sh` 98.00%,
`clean_audio_filters.sh` 91.40%, `transcribe_deps.sh` 92.31%. **All predate
both instrument fixes and may now measure higher — re-measure before writing
a single test for them.**

`rpi_nc_ca.sh` (73/73) and `dot_resolver_install.sh` (39/39) are at 100% and
could come off the allowlist whenever you want, by the three-step bar.

**`nc_php.sh` does not measure at all** — "kcov instrumented no lines", on the
pre-fix instrument too. Not a regression; treat as unverified.

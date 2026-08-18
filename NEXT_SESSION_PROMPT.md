# Next session: §3's next restructure — setup_hosts_guard.sh

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

Over-cap: **12** (11 shell, 2 kotlin, 1 dart). Working tree clean, `main` in
sync as of the diagnose_pacman_hook_stall.sh split commit (see §0.5).

Two standing decisions from the user, already made — do **not** re-litigate:

1. **100% line coverage on what you extract** — same bar every session so far
   has applied.
2. **Split blind where there is no device.** Do not deploy to the phone, do
   not ask to. Prove splits with tests, hashes and real runs instead.

---

## 0. What just happened (read this, don't repeat it)

Two sessions ago: `install_plagiarism_tools.sh` was split (534→94 lines +
3 libs, 100% coverage) — then the user said they no longer use the
plagiarism tools at all, so the whole thing was archived to
`kuhyx/testsAndMisc-archive` with full git history via `git filter-repo`.
One session ago: the same one-line "do you still use this?" check-in was
asked about `libre_translate.sh` _before_ any code was touched, and got the
same answer — also archived, not split.

**Lesson (2 for 2, now reinforced a third way):** keep asking the check-in
before every future §3/§4 split. It is not a formality; it has changed scope
in both of the two times it's been tried.

## 0.5. What just happened (this session) — diagnose_pacman_hook_stall.sh split, confirmed live

Asked the dead-code check-in first, per §0's lesson. User confirmed this
script **is** still in active use (unlike the last two candidates) — so the
split proceeded as originally planned. 493 lines → 249 (entry) + 6 libs
(pacman_hook_stall_setup.sh, _load.sh, _capture.sh, _watch.sh, _usage.sh,
_summary.sh), all at 100% line coverage, plus a PATH-shim test suite (56
lib-level + 13 entry-level subprocess assertions, 0 failed).

**Two things worth knowing before touching this area again:**

1. `run_one`/`cleanup`/`log_size`/`main` had to stay together in the entry
   script — they share `PACMAN_PID`/`LAST_ELAPSED` across the `EXIT` trap,
   and a prior session (commit `2527fb3`) already proved that splitting
   `run_one` into a lib produces a **real** SC2153/SC2034 pair (not a
   suppressible false positive), because a sourced lib has no way to declare
   where its globals come from. If a future split looks like it wants to
   move a function that both writes a global the entry script reads AND
   reads a global only the entry script sets, do the same scratch
   shellcheck-dry-run check (with `.shellcheckrc`'s `external-sources=true` /
   `source-path=SCRIPTDIR`, which is what the real hook uses) **before**
   committing to a lib boundary, not after.
2. **kcov cannot see `done <redirect>`, `} >redirect`, or lines inside an
   inline awk script**, no matter how thoroughly the code executes (verified
   empirically with `bash -x` on isolated repros — those lines never emit a
   trace event). If a coverage gap on a future file's line list looks
   suspiciously like a loop-closing or group-closing line, or an awk block,
   check whether it's this exact class before assuming the test is weak. The
   user was asked and chose "refactor the code" over "fix the coverage
   tool" — that decision holds for this repo going forward unless
   re-raised.
3. **Test files are not exempt from the 250-line cap.** The entry-script
   subprocess test grew to 295 lines while adding coverage and had to be
   split itself, mid-session, after `check_file_length.sh --all` caught it.
   Budget for this: a test file that drives real subprocess timing (unshare,
   real sleep, multiple flag combinations) grows fast — split its fixture
   setup into a shared harness early rather than after it's already over.
4. Evidence + contract:
   `docs/superpowers/evidence/split-diagnose-pacman-hook-stall-2026-08-18.json`
   and the matching `contracts/` file are the current format reference —
   more detailed than the plagiarism-tools pair since this split involved
   several genuine (not mechanical) function rewrites, all individually
   justified there.

## 1. This session's task: `setup_hosts_guard.sh`

Location:
`linux_configuration/scripts/periodic_background/hosts/guard/setup_hosts_guard.sh`
(576 lines).

**Ask the dead-code check-in first** (see §0.5) — the streak is 2-for-3 so
far (2 archived, 1 confirmed live); don't assume either outcome.

**Before you start**, confirm scope hasn't drifted: `git status --short` and
`wc -l` on the target file, and re-run
`bash meta/scripts/check_file_length.sh --all` to get the current exact
list — files change size between sessions, and this file's line count may
not still be 576.

Check what this file references before planning a split boundary —
`hosts_guard_migrate.sh`/`hosts_guard_rollback.sh` already exist as siblings
in `linux_configuration/scripts/single_use/fixes/lib/`, and
`fixes/migrate_hosts_guard_to_guard_lib.sh` is the entry script that
migrated _to_ this guard-lib system. Read that migration script's header
comment first — it explains what guard-lib actually does and may reveal
whether `setup_hosts_guard.sh` itself is now redundant with the migrated
state, which is exactly the kind of thing the dead-code check-in is for.

## 3. §4 — do not touch this session

`install_leechblock.sh` (485) and `block_compulsive_opening.sh` (705) are
copied to `/usr/local/…`, and `pacman_wrapper.sh:831` prefers the deployed
copy on **every pacman invocation**. Splitting them naively breaks every
`pacman -S` on this machine. Out of scope until `setup_hosts_guard.sh` is
done (or archived) and the user explicitly says to continue into §4.

You cannot run `sudo pacman -S` from the Bash tool — it deadlocks on
`db.lck`. Hand the user a `! sudo pacman -S <pkg>` line plus the expected
output if `pacman_wrapper.sh` ever needs live verification.

## 4. Out of scope until the user says otherwise

`setup_midnight_shutdown.sh` (1734), `check_and_enable_services.sh` (1301),
`generate_study_materials.sh` (1017), `pacman_wrapper.sh` (929),
`setup_night_lockdown.sh` (918), `hosts/install.sh` (912),
`EnforcementRunner.kt` (564), `DevicePolicyBridge.kt` (415),
`status_page_state.dart` (307) — check `check_file_length.sh --all` for the
current exact list before assuming this is still accurate, since files
change size between sessions.

`pacman_wrapper.sh` carries the same live-deployment trap as §3/§4. The
Kotlin and Dart files need a different verification stack — `focus_owner`
gradle needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and `--rerun-tasks`; a
plain `gradlew test` reports `UP-TO-DATE` and proves nothing.

## 5. Rules that will bite you (carried forward, still true)

- **Ask before large scope changes.** Two of the last three sessions turned
  into archive-and-delete mid-session because the user volunteered new
  information partway through (or, this session, confirmed the file WAS
  still live). That is fine and expected — just don't assume silence means
  "keep going as originally scoped" if something about the target file's
  relevance seems worth a quick check.
- **No suppressions, ever.** No `# noqa`, no per-file-ignore added without
  asking every time, no shellcheck disable beyond what's already justified
  inline. If a coverage or lint finding looks like it fundamentally
  conflicts with the file's purpose, ask before working around it — this
  session's kcov-blind-spot finding (§0.5.2) is the exact pattern: verify
  the finding is real (bash -x trace check) before assuming it's a tool
  limitation to route around vs. a real behavioral gap to test.
- **A file must not assign a global it never reads** (SC2034). The hook runs
  `shellcheck` with **no `-x`**, but `.shellcheckrc`'s
  `external-sources=true` + `source-path=SCRIPTDIR` means a `source=`
  annotation on the _sourcing_ file still resolves correctly — the failure
  mode that actually breaks is a _lib_ file trying to reference a global
  only the entry script sets, since a lib has no annotation pointing
  "upward" to whoever sources it. Constants travel with their readers; a
  global genuinely written on both sides of a seam stays in the entry
  script.
- **New sourced libs need a shebang AND the executable bit**, even though
  they're sourced, not executed — `lib/hosts_guard_migrate.sh` and this
  session's 6 new libs both carry `100755` in the git index, matching
  convention. The hook reads the **git index**: stage with
  `git add --chmod=+x`, and note that a plain `git add` afterwards resets
  it.
- `pre-commit run --files <changed>` before committing, but run it **after**
  `git add`, not before — index-mode checks (executable bit) only fire
  against what's staged. **`prettier` and `ci-mirror` run on pre-push.**
  `npx prettier --write` any `.md`/`.json` you touch (evidence/contract files
  included — they are JSON and prettier will reformat them).
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`. Staging **≥4 code files
  also needs** a fresh `docs/superpowers/contracts/*.json`. Put the
  **measured** coverage number in it, not a rounded-up one. This session's
  pair (`split-diagnose-pacman-hook-stall-2026-08-18.json` in both
  `evidence/` and `contracts/`) is the current best format reference —
  it documents several genuine mid-session findings (a real bug, a
  memory-safety catch, a test-file-too-long split) as they happened, which
  is the level of detail to aim for when the session isn't a pure mechanical
  move.
- Work directly on `main`. `git stash` and branch creation are blocked; use
  `git worktree add --detach` for a clean baseline (but NEVER `git filter-repo`
  inside a worktree — it shares the object store with the main repo and will
  corrupt it; always a throwaway `git clone` for that).
- **Do not wire the file-length hook into pre-commit.** It lands last, once
  `check_file_length.sh --all` exits 0.
- Watch `jscpd` (fails above 2%). Measure in a **clean HEAD worktree**
  (`git worktree add --detach <tmp> HEAD`, copy the new files in, run jscpd
  there, remove the worktree) — the working tree reads higher because of
  vendored `.venv`, and several near-identical test files sharing a fixture
  preamble is exactly the shape that trips this gate.
- Cap pytest memory:
  `systemd-run --user --scope -p MemorySwapMax=0 -p MemoryMax=2G`.
- **Never let a test allocate unbounded real memory.** This session's
  `--with-load` entry test would have `dd`ed 13-20+ GB into `/dev/shm` using
  this box's real available memory before it was caught in review — any
  script under test that computes an allocation size from real
  `/proc/meminfo` needs its floor/ceiling constants made env-overridable
  (`: "${VAR:=default}"`, not a bare or `readonly` assignment) so tests can
  pin them to a small, bounded amount instead of trusting the live system
  state to stay favorable.

## 6. Tooling reference

**`meta/scripts/check_file_length.sh --all`** — the 250-line gate. Run
**before every commit**. Applies to test files too, not just the file
you're splitting.

**`meta/scripts/shell_coverage.sh <test> <subject> [min]`** — kcov wrapper,
100% minimum. Hand it the test script **directly**; `bash script.sh`
instruments the bash binary and silently reports 0/0. If a test suite for
one subject is split across multiple test files, `shell_coverage.sh` only
takes one at a time — run kcov manually into the same output dir for each
test file, then call `meta/scripts/shell_coverage_report.py <outdir> <subject> <min>`
once to get the merged number (it sums hits per line-number across every
`cov.xml` it finds, so multiple runs against the same subject combine
correctly).

**`meta/scripts/extract_shell_functions.py`** — moves functions
brace-by-brace. **Never slice by line range**. **Do not trust where it puts
the source line** — verify with `grep -c` on the anchor and check placement.
The `--header` text is written **verbatim, uncommented** — pass a full
`#!/bin/bash\n# comment` string, not bare prose, or the generated lib won't
parse.

**`meta/scripts/verify_shell_split.sh <pre-split-rev> <old> <new>...`** —
proves a split moved every function verbatim (hashes function bodies only,
blind to top-level code). For a **partial** split list the old path among the
new paths too, or it reports a false `DIFFERENCE`. A function that was
genuinely rewritten (not moved) will legitimately show as `DIFFERENCE` —
that's expected, not a bug; explain it in evidence rather than trying to make
the tool agree.

**`meta/scripts/mutate_shell.py <spec>`** — mutation testing against specs in
`meta/scripts/fixtures/mutations/`. No spec exists for anything outside
`phone_focus_mode/`; optional, not required — 100% line coverage with real
assertions is the stated bar.

## 7. Testing pattern to follow

The established pattern for `single_use/`-adjacent shell scripts with no
prior test coverage (now used across three splits):

- A `lib/tests/` directory sibling to the split libs.
- A `*_harness.sh` file (sourced, not executed) with `_t_pass`/`_t_fail`/
  `_t_eq` helpers, `mktemp -d` + `trap cleanup EXIT`, and PATH-shim fakes for
  any external tool the code shells out to (record invocation to a file,
  minimum realistic behavior).
- One `test_<lib>.sh` per lib, sourcing the harness, asserting against real
  function calls (not mocks at the call-site level).
- A `test_<entry-script>.sh` that runs the **actual entry script as a
  subprocess** against the same fakes, since `verify_shell_split.sh` and kcov
  are blind to code that only lives in the entry script's `main()`. If this
  test file threatens to grow past 250 lines (it will, once you're covering
  several arg combinations and timing branches), split the fixture setup
  into its own `*_entry_harness.sh` early and write two or more thinner test
  files against it — this session had to do this mid-stream and it's
  cheaper to plan for upfront.
- Sharp edges hit and fixed across sessions, watch for all of them again:
  - `local a="$1" b="${a}"` **fails under `set -u`** — bash evaluates all
    RHS expressions in the new scope before any assignment lands. Split into
    separate `local` statements.
  - A function that calls `exit` (not `return`) on a fatal condition will
    kill the whole test script if called directly inside an `if` condition.
    Run it in a subshell: `if (fn args); then ...`.
  - A backgrounded process needs `disown` before `kill`/`wait` reliably
    affects only it, not the calling job — this bit both a `stop_load` test
    and the entry script's SIGTERM test this session.
  - **SIGINT delivery to a backgrounded job was unreliable in this
    environment; SIGTERM was not.** If a script's trap handles both signals
    identically (`trap handler EXIT INT TERM`), prefer testing via SIGTERM.
  - If a script under test computes a real resource allocation (memory,
    disk) from live system state, make the relevant constants
    env-overridable and pin them to something tiny in every test — never
    trust "the box currently has enough headroom" to stay true.

Check the target file for anything that shells out (pacman? systemctl?
journalctl? guardctl?) before assuming a prior session's fakes apply — each
file is a different domain, so the PATH-shim list will differ.

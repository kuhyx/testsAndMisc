# Next session: Phase-driven campaign — CI green → 250-cap zero → gates → shell coverage

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

This file drives a **multi-session campaign** with four phases, run strictly
in order. Do not skip ahead to a later phase while an earlier one is
incomplete — re-check the phase's exit condition at the start of every
session, even if this doc claims it's done, since state can drift between
sessions.

**The user's request that created this campaign** (verbatim intent): make it
true FOR SURE that all files are under the 250-line cap, then add a 100%
shell test-coverage gate, then add a pre-commit rule that blocks commits when
any file is over 250 lines AND checks that GitHub Actions is green on this
repo.

## How to run this session (read before anything else)

**Do not ask "should I continue?" between files.** The queue below is already
approved. Work it to completion, or until you hit a genuine design fork or an
irreversible action. Ending a turn to narrate progress mid-queue is a bug —
summarise once, at the end. This was violated twice in the previous session
despite being written in `~/.claude/memories/workflow-rules.md`; it is
repeated here because the standing rule alone did not hold.

**Standing decisions — do NOT re-litigate:**

1. **100% line coverage on what you extract/write tests for** — same bar
   every prior split has used.
2. **Split blind where there is no device.** Do not deploy to the phone, do
   not ask to. Prove splits with tests, hashes and real runs instead.
3. **CI must be fixed before any new gate is added.** (Phase 0 is done; this
   just means don't add a gate on top of a red baseline if CI regresses.)
4. **The shell coverage gate is a NEW, separate requirement** covering every
   `.sh` file repo-wide. That is Phase 3 — do not conflate it with Phase 1.

The old "one file split per session" pacing decision is **superseded**: the
user explicitly asked for multiple files per session ("this is a very slow
way of doing it"). Batch through the queue.

---

## Phase 0: CI green — **DONE 2026-08-18, re-verify only**

`gh run list --limit 5` should show `Pre-commit checks`, `Shell tests` and
`Python tests` green on `main`. Fixed by adding `librsvg2-bin` to both
workflows (`4326ea4`) and making `python-tests.yml` self-triggering +
`workflow_dispatch` (`4a35be7`).

**Two traps worth keeping:**

- `python-tests.yml` is path-filtered. A commit touching only workflow files
  or only non-Python paths will NOT trigger it — that is expected, not a
  failure. Check the workflow's own last run rather than assuming.
- `gh run rerun` replays the **historical commit's** workflow YAML, not
  `main`'s current one. It cannot verify a workflow-file fix. Push a real
  commit under a watched path instead.

## Phase 1: Drive the 250-line cap to zero — **IN PROGRESS, 8 files left**

Re-run `bash meta/scripts/check_file_length.sh --all` first; the list drifts.

```
1734  linux_configuration/scripts/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh
1225  linux_configuration/scripts/periodic_background/check_and_enable_services.sh
1017  linux_configuration/scripts/single_use/utils/generate_study_materials.sh
 929  linux_configuration/scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh
 918  linux_configuration/scripts/periodic_background/digital_wellbeing/setup_night_lockdown.sh
 913  linux_configuration/scripts/periodic_background/hosts/install.sh
 705  linux_configuration/scripts/periodic_background/digital_wellbeing/block_compulsive_opening.sh
 485  linux_configuration/scripts/periodic_background/digital_wellbeing/install_leechblock.sh
```

**Everything remaining is a shell script.** All three `focus_owner` files are
done (`47e05d1`, `6efb4ba`, `7d7b3c7`) — that repo is confirmed live and
enforcing, not a dead-code candidate.

### The queue, in this order

**Safe tier — do these first, no deployment trap:**

1. `check_and_enable_services.sh` (1225) — a `lib/` already exists beside it
   at `linux_configuration/scripts/periodic_background/lib/` (currently holds
   only `periodic_browser.sh`), but **no `lib/tests/` yet** — you will create
   it. Referenced by `install_makepkg_wrapper.sh` and
   `pacman/lib/integrity.sh`.
2. `generate_study_materials.sh` (1017) — referenced by `repo_to_study.sh`
   and `lib/repo_study_steps.sh`; a `lib/` with `repo_study_steps.sh` already
   exists beside it.
3. `hosts/install.sh` (913) — **widest reference surface of the three: 13
   referencing files**, including `install_core_system.sh`,
   `setup_periodic_system.sh`, `fresh-install/main.sh` and
   `phone_focus_mode/deploy_phases.sh`. Handle with more care than its line
   count suggests; `grep -rl` before and after.

All three were confirmed live/referenced — **none is an archive candidate**,
so don't spend a round asking "do you still use this?" for these three.

**Deployment-trap tier — 4 files, handle last and very carefully:**

`setup_midnight_shutdown.sh`, `pacman_wrapper.sh`, `install_leechblock.sh`,
`block_compulsive_opening.sh`. These are copied to `/usr/local/…` and
`pacman_wrapper.sh` prefers the deployed copy on **every pacman invocation**
— a naive split breaks `pacman -S` on this machine. Re-verify the mechanism
before assuming (`grep -n "prefer\|deployed" pacman_wrapper.sh` near line
831). You cannot run `sudo pacman -S` from the Bash tool (deadlocks on
`db.lck`); hand the user a `! sudo pacman -S <pkg>` line plus the expected
output if live verification is ever needed.

**`setup_midnight_shutdown.sh` additionally needs a non-standard plan.** Its
39 top-level-looking functions are NOT all real: several (`log`,
`now_epoch`/`current_epoch`, `cmd_add`/`cmd_list`/`cmd_remove`,
`require_root`) are duplicated because the outer script _generates_ inner
standalone scripts via heredocs (`create_shutdown_check_script`,
`create_override_manager_script`, `install_monitor_service`) that get written
to `/usr/local/bin/`. `extract_shell_functions.py` and
`verify_shell_split.sh` both assume real top-level functions and will
mishandle a heredoc body. The plan that will work: extract only the genuine
outer orchestration functions, treat each `create_*_script` heredoc as one
atomic unit that moves whole (never split its interior), and verify by
hashing the _emitted_ `/usr/local/bin/*` content before and after
(`sha256sum` on a rendered-heredoc temp file), not just by running
`verify_shell_split.sh` on the outer file.

### Reference split to copy

`linux_configuration/scripts/single_use/fixes/lib/` + `lib/tests/` is the
worked example — look at the `pacman_hook_stall_*` family:

- `lib/tests/pacman_hook_stall_harness.sh` — sourced, not executed;
  `_t_pass`/`_t_fail`/`_t_eq`, `mktemp -d` + `trap cleanup EXIT`, PATH-shim
  fakes for external tools.
- `lib/tests/pacman_hook_stall_entry_harness.sh` — separate fixture setup for
  the entry-script test, split out early so neither file passes 250 lines.
- One `test_<lib>.sh` per lib, asserting against real function calls.
- `test_diagnose_pacman_hook_stall_*.sh` — runs the **actual entry script as
  a subprocess** against the same fakes.

### Tooling

- `meta/scripts/check_file_length.sh --all` — the gate. Run before every
  commit. Applies to test files too.
- `meta/scripts/extract_shell_functions.py` — moves functions brace-by-brace.
  **Never slice by line range.** Verify placement with `grep -c` on the
  anchor.
- `meta/scripts/verify_shell_split.sh <pre-split-rev> <old> <new>...` —
  proves every function moved verbatim. For a **partial** split, list the old
  path among the new paths too.
- `meta/scripts/shell_coverage.sh <test> <subject> [min]` — kcov wrapper,
  100% minimum. Hand it the test script **directly**; `bash script.sh`
  instruments the bash binary and silently reports 0/0.

### Sharp edges that have bitten before

- `local a="$1" b="${a}"` **fails under `set -u`** — separate `local`
  statements.
- A function that calls `exit` (not `return`) kills the whole test script if
  called directly in an `if` condition. Use a subshell: `if (fn args); then`.
- A backgrounded process needs `disown` before `kill`/`wait` behaves.
- **SIGINT to a backgrounded job was unreliable here; SIGTERM was not.**
- If a script computes a real resource allocation from live system state,
  make the constants env-overridable and pin them tiny in every test.
- **A file must not assign a global it never reads** (SC2034). The hook runs
  `shellcheck` with no `-x`, but `.shellcheckrc`'s `external-sources=true` +
  `source-path=SCRIPTDIR` means a `source=` annotation on the _sourcing_ file
  still resolves.
- **New sourced libs need a shebang AND the executable bit**, staged with
  `git add --chmod=+x` — a plain `git add` afterwards resets it.

**Exit condition for Phase 1:** `check_file_length.sh --all` exits 0.

## Phase 2: Wire the file-length gate into pre-commit

**Do NOT start until Phase 1 exits 0** — wiring it early breaks every commit
repo-wide, including unrelated ones.

1. Add a `local` hook to `.pre-commit-config.yaml` running
   `bash meta/scripts/check_file_length.sh --all`, following the existing
   `language: system` + `pass_filenames: false` shape (see
   `ai-evidence-contract` / `no-polling-antipatterns`). Repo-wide, not
   per-file: a file that grows past 250 lines without being staged this
   commit should still be caught.
2. **GitHub-Actions-green check — GENUINE DESIGN FORK, ask the user first.**
   A pre-commit hook cannot block on "is CI green" for a commit that does not
   exist yet. Two real options:
   - **(a)** check the latest run on `main` is green before allowing a new
     commit — catches "building on a known-broken baseline", not "did MY
     change break it";
   - **(b)** a **pre-push** hook running the CI workflows' local equivalent
     before allowing the push — closer to the real guarantee, and `ci-mirror`
     already does this for the Python/pre-commit side. Extending it to also
     run `Shell tests`' local equivalent is likely the more honest answer.

   This is the one place in Phases 1–2 where stopping to ask is correct.

3. Verify by making a throwaway file exceed 250 lines, confirming the commit
   is blocked with a clear message, then removing it.

## Phase 3: Repo-wide 100% shell coverage gate — largest phase, many sessions

**Do NOT start until Phases 1 AND 2 are done.**

487 `.sh` files exist repo-wide vs ~15 `lib/tests/` dirs following the
established pattern — on the order of 450+ untested scripts, roughly an order
of magnitude more work than Phase 1. Re-count before starting.

**Ask the user to confirm scope before starting Phase 3 at all**, and ask
whether the gate should be repo-wide from day one or **ratchet** (only new or
modified files must be covered, with a shrinking allowlist of pre-existing
untested files). A hard repo-wide gate would block unrelated commits to any
of 450+ files until every one has tests. Recommend the ratchet, but it is the
user's call.

---

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, no per-file-ignore without asking
  every time, no new shellcheck disable.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`. Staging **≥4 code files
  also needs** a fresh `docs/superpowers/contracts/*.json`. Put the
  **measured** number in it, not a rounded one.
- **An archive does not need new tests.** The 100%-coverage rule binds code
  that is _split_ or newly _written_, not code that is _deleted_.
- **A test file broken by your commit is a same-session bug, not a TODO.**
  Run `gh run list` after every push — CI-only suites (like
  `linux_configuration/tests/*.sh` run directly by `shell-tests.yml`) are not
  caught by pre-commit's file-scoped hooks.
- `pre-commit run --files <changed>` **after** `git add`. `prettier` and
  `ci-mirror` run on **pre-push**. `npx prettier --write` any `.md`/`.json`
  you touch, evidence and contract files included.
- Work directly on `main`. `git stash` and branch creation are blocked; use
  `git worktree add --detach` for a clean baseline (but NEVER
  `git filter-repo` inside a worktree — it shares the object store and will
  corrupt the main repo; always a throwaway `git clone` for that).
- Watch `jscpd` (fails above 2%). Measure in a clean HEAD worktree.
- Cap pytest memory:
  `systemd-run --user --scope -p MemorySwapMax=0 -p MemoryMax=2G`.
- **Known tooling bug, fix opportunistically:**
  `~/.claude/scripts/dart_format_changed.sh <repo>` reports "No changed Dart
  files" even when files changed, if invoked with a repo path from outside
  that repo — it `cd`s into `$repo` then runs `git status --porcelain`, whose
  paths are relative to the **git worktree root**, so its `[[ -f $path ]]`
  check fails for every file. Workaround used: `dart format <files>` directly.
  Real fix: `cd` to the git toplevel, or strip the prefix.

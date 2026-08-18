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

Two standing decisions from the user, already made — do **not** re-litigate:

1. **100% line coverage on what you extract/write tests for** — same bar
   every prior split has used.
2. **Split blind where there is no device.** Do not deploy to the phone, do
   not ask to. Prove splits with tests, hashes and real runs instead.

Three decisions made when this campaign was scoped (2026-08-18) — also do
**not** re-litigate without asking first:

3. **This is a recurring driver, not a single mega-session.** One phase step
   per session (usually one file split, or one CI fix), same pace as every
   split so far. Update this file at the end of each session for the next.
4. **CI must be fixed before any new gate is added.** A "must be green" gate
   is meaningless while CI is already red for unrelated reasons.
5. **The new shell coverage gate is a NEW, separate requirement** covering
   every `.sh` file repo-wide (not just newly-split ones). This is Phase 3,
   explicitly the largest phase — do not conflate it with Phase 1's cap work.

---

## Phase 0: Fix current CI red state — **STATUS: in progress, check first**

Three workflows were found red on `main` as of 2026-08-18, discovered while
scoping this campaign:

1. **`Pre-commit checks` AND `Python tests` workflows — same root cause,
   both persistent and predating this campaign.** Both fail with
   `FAIL Required test coverage of 100% not reached. Total coverage: 99.98%`
   (6565 lines/1 miss, 1630 branches/1 miss). The gap is
   `python_pkg/artgate/routes/vector.py:156` (95% coverage in CI). Root
   cause: CI logs show `SKIPPED python_pkg/artgate/tests/test_routes.py:124:
rsvg-convert not installed` — the `ubuntu-latest` GitHub Actions runner
   lacks `rsvg-convert`, so a test that would cover line 156 doesn't run
   there, while it passes locally (and in the pre-push `ci-mirror` hook,
   confirmed — that hook passed on both of this session's pushes) where
   `rsvg-convert` is installed. **This predates this campaign by at least a
   day** — `Python tests` was already failing with the identical signature
   on 2026-08-17 commits (`vscode_optimizer: split...`,
   `transcribe_helpers: split...`, etc.), long before the hosts-guard
   archive started. **Not yet fixed** — pick this up first, it blocks BOTH
   workflows simultaneously since they share the same coverage command.
   Likely fix: add `rsvg-convert` (librsvg) to whichever GitHub Actions
   runner setup step precedes pytest in `.github/workflows/pre-commit.yml`
   and `.github/workflows/python-tests.yml`, OR make the skipped test's
   coverage line conditionally excludable when the tool is genuinely absent
   (ask the user which they'd rather have — installing the real dependency
   in CI is almost certainly correct here, but confirm before choosing an
   `# pragma: no cover`-style route given the no-suppressions rule).
2. **`Shell tests` workflow** — was also red (this campaign's own earlier
   commit broke `test_hosts_guard_pacman_integration.sh` by archiving files
   it referenced). **Already fixed** this session, commit `e48f253`, and
   confirmed green on the very next push (`gh run view 32185366621` →
   `success`). Re-verify it's still green before trusting this note
   (`gh run list --limit 3`) — don't assume it stayed fixed if something
   else touched shell tests since.

**Exit condition for Phase 0:** `gh run list --limit 5` shows the most
recent run of `Pre-commit checks`, `Python tests`, AND `Shell tests` on
`main` all as `success`. Do not proceed to Phase 1 until this is true. If a
session starts and Phase 0 isn't done, finish it before touching anything
else — don't let it linger while new work piles on top of a broken
baseline.

## Phase 1: Drive the 250-line cap to zero

**Status as of 2026-08-18: 11 files over cap.** Re-run
`bash meta/scripts/check_file_length.sh --all` at the start of every session
in this phase — the exact list drifts as other work touches these files.

```
1734  linux_configuration/scripts/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh
1225  linux_configuration/scripts/periodic_background/check_and_enable_services.sh
1017  linux_configuration/scripts/single_use/utils/generate_study_materials.sh
 929  linux_configuration/scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh
 918  linux_configuration/scripts/periodic_background/digital_wellbeing/setup_night_lockdown.sh
 913  linux_configuration/scripts/periodic_background/hosts/install.sh
 705  linux_configuration/scripts/periodic_background/digital_wellbeing/block_compulsive_opening.sh
 564  focus_owner/android/app/src/main/kotlin/com/kuhy/focus_owner/EnforcementRunner.kt
 485  linux_configuration/scripts/periodic_background/digital_wellbeing/install_leechblock.sh
 415  focus_owner/android/app/src/main/kotlin/com/kuhy/focus_owner/DevicePolicyBridge.kt
 307  focus_owner/lib/status_page_state.dart
```

**Two of these carry a live-deployment trap, handle last or very carefully:**
`install_leechblock.sh` and `block_compulsive_opening.sh` are copied to
`/usr/local/…`, and `pacman_wrapper.sh:831` prefers the deployed copy on
**every pacman invocation**. Splitting them naively breaks every
`pacman -S` on this machine. `pacman_wrapper.sh` itself carries the same
trap (it IS the thing that prefers the deployed copies). Re-verify this is
still true before assuming the old note holds — a lot changed guard-lib-side
in the session that wrote this doc, worth the 30-second re-check
(`grep -n "prefer\|deployed" pacman_wrapper.sh` near line 831).

You cannot run `sudo pacman -S` from the Bash tool — it deadlocks on
`db.lck`. Hand the user a `! sudo pacman -S <pkg>` line plus the expected
output if `pacman_wrapper.sh` ever needs live verification.

The Kotlin and Dart files need a different verification stack —
`focus_owner` gradle needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and
`--rerun-tasks`; a plain `gradlew test` reports `UP-TO-DATE` and proves
nothing.

**Before splitting ANY file in this list, run the dead-code check-in first**
(ask the user: "do you still use this?"). This lesson has held 3 of the last
4 sessions — files on this list have turned out to be fully superseded by
something else (guard-lib replaced the entire hosts-guard subsystem this
way). Don't assume a file needs splitting just because it's long; it might
need archiving instead. When surveying a candidate for archival, survey its
**whole directory and cross-references** (`grep -rl <name>` repo-wide), not
just the named file — this has changed scope from "split one file" to
"archive 17 files" once already.

**Exit condition for Phase 1:**
`bash meta/scripts/check_file_length.sh --all` exits 0 with no files listed.
Do not proceed to Phase 2 until this is true.

## Phase 2: Wire the file-length gate into pre-commit

**Do NOT do this until Phase 1's exit condition is met.** Wiring it early
breaks every commit repo-wide, including unrelated ones, for as long as
Phase 1 remains incomplete.

Once `check_file_length.sh --all` exits 0:

1. Add a `local` hook to `.pre-commit-config.yaml` that runs
   `bash meta/scripts/check_file_length.sh --all` and fails the commit
   (non-zero exit) if any file is found. Follow the existing local-hook
   pattern already in the file (see e.g. the `ai-evidence-contract` or
   `no-polling-antipatterns` hooks for the `language: system` +
   `pass_filenames: false` shape — this check is repo-wide, not
   per-file, since a file that grows past 250 lines without being staged
   this commit should still be caught).
2. Also add the GitHub-Actions-green check here (see below) if it hasn't
   been added yet — the user asked for both in the same pre-commit rule,
   though they can land as two hooks in the same commit rather than one
   combined script if that's cleaner.
3. **GitHub-Actions-green check, exact mechanism to decide with the user
   first (ask, don't assume):** a pre-commit hook cannot literally block a
   commit on "is CI green" for a commit that doesn't exist yet — CI runs
   AFTER a push, not before a commit. Two real options:
   - **(a) Check the LATEST run on `main` is green** before allowing a new
     commit — catches "you're building on top of a known-broken baseline"
     but not "did MY change break something," since that can only be known
     after pushing.
   - **(b) A pre-PUSH hook** (this repo already has a pre-push stage, see
     `ci-mirror`) that runs the equivalent of the CI workflows locally
     before allowing the push — closer to the actual guarantee wanted, and
     `ci-mirror` already does exactly this for the Python/pre-commit side.
     Extending it (or adding a sibling hook) to also run the `Shell tests`
     workflow's local-equivalent commands before push may be the more
     honest way to satisfy "checks GitHub workflow outputs green" than
     querying `gh run list` for a run that hasn't happened yet.

   Ask the user which they want (or both) before implementing — this is a
   genuine design fork, not a mechanical step.

4. Verify by making a throwaway file exceed 250 lines and confirming the
   commit is actually blocked with a clear error message, then removing the
   throwaway file, before considering this phase done.

**Exit condition for Phase 2:** the new hook(s) exist in
`.pre-commit-config.yaml`, `pre-commit run --files <touched>` fails when a
file exceeds 250 lines (verified with a throwaway test), and the mechanism
chosen for the CI-green check is documented in this doc's next revision.

## Phase 3: Repo-wide 100% shell coverage gate — **the largest phase, expect many sessions**

**Do NOT start this until Phase 1 AND Phase 2 are both done.** This is
explicitly scoped as separate, much larger work — do not let it bleed into
or block the 250-cap campaign.

**Scale, measured 2026-08-18:** 487 `.sh` files exist repo-wide (excluding
`.venv/`, vendored, and build-output dirs) versus only 14 `lib/tests/`
directories following the established split-and-test pattern. A genuinely
repo-wide "100% line coverage, every shell script" gate would immediately
demand test suites for on the order of 450+ currently-untested scripts. This
is roughly an order of magnitude more work than Phase 1's 11 files. Re-count
before starting (`find . -name '*.sh' -not -path '*/.venv/*' -not -path
'*/node_modules/*' -not -path '*/testsAndMisc_builds/*' -not -path
'*/testsAndMisc_binaries/*' -not -path '*/.git/*' | wc -l`), since Phase 1
will have grown the tested-file count somewhat.

**Ask the user to confirm scope before starting Phase 3 at all** — 487
files is a genuinely large body of future work and deserves an explicit
"yes, still want this" check before a session starts writing hundreds of
test files, not just a paste of an old plan. Also ask whether the gate
should apply repo-wide from day one (blocking ANY commit touching an
untested `.sh` file) or ratchet in incrementally (e.g. only newly-added or
newly-modified files must be covered, with a frozen allowlist of
pre-existing untested files that shrinks over time) — a hard repo-wide gate
turned on immediately would block unrelated commits to any of the 450+
untested files until every one of them gets a test suite, which could stall
unrelated work for a long time. A ratcheting gate is the much more common
pattern for retrofitting coverage onto an existing codebase and is worth
raising as the recommended default, but it's the user's call.

Use `meta/scripts/shell_coverage.sh <test> <subject> [min]` (kcov wrapper)
and the established `lib/tests/` + harness + PATH-shim pattern from every
split so far (see Phase 1's testing-pattern reference below) — there is no
reason for shell test infrastructure to differ between "coverage added
because we split the file" and "coverage added because a new gate demands
it."

**Exit condition for Phase 3:** every `.sh` file in the repo (or every file
not on an explicitly agreed allowlist, if ratcheting was chosen) has a test
suite reaching the agreed minimum coverage, and a pre-commit/CI gate enforces
it going forward. Given the scale, expect this phase's "exit condition" to
itself be revised into something more incremental once the user weighs in.

---

## Rules that will bite you (carried forward, still true)

- **Ask before large scope changes.** Repeatedly, a check-in or a directory
  survey has surfaced something bigger than the named task. That's expected —
  don't assume silence means "keep going as originally scoped."
- **Survey the whole directory before scoping an archive, not just the named
  file.** `grep -rl <filename-stem>` across the repo, then `ls` the file's
  own directory.
- **No suppressions, ever.** No `# noqa`, no per-file-ignore added without
  asking every time, no shellcheck disable beyond what's already justified
  inline. This applies to Phase 0's coverage gap too — don't reach for a
  coverage-exclude pragma without asking first; installing the missing
  dependency in CI is the more likely correct fix.
- **A file must not assign a global it never reads** (SC2034). The hook runs
  `shellcheck` with **no `-x`**, but `.shellcheckrc`'s
  `external-sources=true` + `source-path=SCRIPTDIR` means a `source=`
  annotation on the _sourcing_ file still resolves correctly.
- **New sourced libs need a shebang AND the executable bit**, staged with
  `git add --chmod=+x` — a plain `git add` afterwards resets it.
- `pre-commit run --files <changed>` before committing, but run it **after**
  `git add`. **`prettier` and `ci-mirror` run on pre-push.** `npx prettier
--write` any `.md`/`.json` you touch (evidence/contract files included).
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`. Staging **≥4 code files
  also needs** a fresh `docs/superpowers/contracts/*.json`. Put the
  **measured** number in it, not a rounded-up one.
- **An archive does not need new tests.** The 100%-coverage standing
  decision binds code that gets _split_ or newly _written_, not code that
  gets _deleted_.
- **A test file broken by an archive commit is a same-session bug, not a
  future TODO.** This campaign already hit this once
  (`test_hosts_guard_pacman_integration.sh`, fixed in `e48f253`) — `gh run
list` after every push, not just `pre-commit run --files <staged>`
  locally, since CI-only test suites (like `linux_configuration/tests/*.sh`
  run directly by `shell-tests.yml`) aren't caught by pre-commit's
  file-scoped hooks.
- Work directly on `main`. `git stash` and branch creation are blocked; use
  `git worktree add --detach` for a clean baseline (but NEVER
  `git filter-repo` inside a worktree — it shares the object store with the
  main repo and will corrupt it; always a throwaway `git clone` for that).
- Watch `jscpd` (fails above 2%). Measure in a **clean HEAD worktree**.
- Cap pytest memory:
  `systemd-run --user --scope -p MemorySwapMax=0 -p MemoryMax=2G`.
- **Never let a test allocate unbounded real memory.**

## Tooling reference

**`meta/scripts/check_file_length.sh --all`** — the 250-line gate. Run
**before every commit**. Applies to test files too, not just the file
you're splitting.

**`meta/scripts/shell_coverage.sh <test> <subject> [min]`** — kcov wrapper,
100% minimum. Hand it the test script **directly**; `bash script.sh`
instruments the bash binary and silently reports 0/0.

**`meta/scripts/extract_shell_functions.py`** — moves functions
brace-by-brace. **Never slice by line range**. Verify placement with
`grep -c` on the anchor.

**`meta/scripts/verify_shell_split.sh <pre-split-rev> <old> <new>...`** —
proves a split moved every function verbatim. For a **partial** split list
the old path among the new paths too.

**`meta/scripts/mutate_shell.py <spec>`** — mutation testing; optional, not
required.

**Archiving a dead file/subsystem** (no dedicated script — hand-run each
time): clone to a scratch dir, `git filter-repo --force --path <each
current path> --path <each historical path from `git log --all --follow
--name-only`>`, clone `testsAndMisc-archive` separately, add the filtered
clone as a remote, `git merge --allow-unrelated-histories`, remove stray
remote-tracking branches and the remote, push, verify with `gh api
repos/kuhyx/testsAndMisc-archive/contents/<dir>`, **then** `git rm` from
`testsAndMisc`. Read
`docs/superpowers/evidence/archive-setup-hosts-guard-2026-08-18.json` for
the full worked example.

## Testing pattern to follow (Phase 1 splits and Phase 3 new coverage alike)

The established pattern for shell scripts with no prior test coverage:

- A `lib/tests/` directory sibling to the split libs.
- A `*_harness.sh` file (sourced, not executed) with `_t_pass`/`_t_fail`/
  `_t_eq` helpers, `mktemp -d` + `trap cleanup EXIT`, and PATH-shim fakes for
  any external tool the code shells out to.
- One `test_<lib>.sh` per lib, sourcing the harness, asserting against real
  function calls (not mocks at the call-site level).
- A `test_<entry-script>.sh` that runs the **actual entry script as a
  subprocess** against the same fakes. If this test file threatens to grow
  past 250 lines, split the fixture setup into its own `*_entry_harness.sh`
  early.
- Sharp edges hit and fixed across sessions, watch for all of them again:
  - `local a="$1" b="${a}"` **fails under `set -u`** — split into separate
    `local` statements.
  - A function that calls `exit` (not `return`) on a fatal condition will
    kill the whole test script if called directly inside an `if` condition.
    Run it in a subshell: `if (fn args); then ...`.
  - A backgrounded process needs `disown` before `kill`/`wait` reliably
    affects only it.
  - **SIGINT delivery to a backgrounded job was unreliable in this
    environment; SIGTERM was not.**
  - If a script under test computes a real resource allocation (memory,
    disk) from live system state, make the relevant constants
    env-overridable and pin them to something tiny in every test.

Check the target file for anything that shells out before assuming a prior
session's fakes apply — each file is a different domain.

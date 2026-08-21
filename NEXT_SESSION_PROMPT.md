# Next session: 250-line cap campaign — 5 files left, all deployment-trap tier

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

**The user's original request** (verbatim intent): make it true FOR SURE that
all files are under the 250-line cap, then add a 100% shell test-coverage gate,
then add a pre-commit rule that blocks commits when any file is over 250 lines
AND checks that GitHub Actions is green on this repo.

Plus a standing instruction from the last session: **fix every real defect you
find along the way**, don't just pin it in a test. Three latent bugs were fixed
that way already (see "Defects found and fixed" below) — keep doing that.

## How to run this session

**Do not ask "should I continue?" between files.** The queue is approved. Work
it to completion, or until a genuine design fork or an irreversible action.
Ending a turn to narrate progress mid-queue is a bug — summarise once, at the
end.

**Standing decisions — do NOT re-litigate:**

1. **Split first, then reach 100% coverage in a SEPARATE follow-up commit.**
   The user chose this explicitly (option b) over doing both at once, because
   it keeps each split provably behaviour-preserving. Record the measured
   coverage number in the evidence JSON either way — never waive it.
2. **One commit per split file**, each with its own evidence JSON _and_ a
   contract JSON (a split always stages ≥4 code files, so the contract gate
   always fires — bake it into the checklist).
3. **Split blind where there is no safe way to run the thing.** Prove splits
   with byte-identical output, textual verification and hashes instead.
4. **Archiving is acceptable if you can prove a file is dead** — no
   references, no installed copy, no unit/timer/hook invoking it. Surface the
   evidence and ask before deleting. Default is split, not delete.

## Phase 0: CI green — verify only

`gh run list --limit 5` should show `Pre-commit checks` and `Shell tests` green
on `main`. Both were green at `47478791`.

Two traps worth keeping:

- `python-tests.yml` is path-filtered. A commit touching only shell paths will
  NOT trigger it — expected, not a failure.
- `gh run rerun` replays the historical commit's workflow YAML, not `main`'s.
  It cannot verify a workflow-file fix; push a real commit instead.

## Phase 1: Drive the cap to zero — 5 files left

Re-run `bash meta/scripts/check_file_length.sh --all` first; the list drifts.

```
1734  linux_configuration/scripts/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh
 929  linux_configuration/scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh
 918  linux_configuration/scripts/periodic_background/digital_wellbeing/setup_night_lockdown.sh
 705  linux_configuration/scripts/periodic_background/digital_wellbeing/block_compulsive_opening.sh
 485  linux_configuration/scripts/periodic_background/digital_wellbeing/install_leechblock.sh
```

**All five are the deployment-trap tier.** The three safe-tier files are done.

### Suggested order: smallest first

`install_leechblock.sh` (485) → `block_compulsive_opening.sh` (705) →
`setup_night_lockdown.sh` (918) → `pacman_wrapper.sh` (929) →
`setup_midnight_shutdown.sh` (1734).

### `install_leechblock.sh` — START HERE, and read this first

This was **attempted and deliberately reverted** last session. The split itself
worked; it was abandoned because of a tooling bug you must not repeat:

> **`shfmt -w` CORRUPTS associative-array keys containing hyphens.**
> `[google-chrome-stable]="Google Chrome"` became
> `[google - chrome - stable]="Google Chrome"` — silently, and it would have
> made browser detection fail entirely. shfmt parses the key as arithmetic.
>
> **Before every `shfmt -w` on a file with a `declare -A`, and again after:**
> `grep -nE '\[[a-z0-9]+ - ' <file>` must come back empty. None of the three
> committed splits are affected (checked); only this file has such keys.

What already worked, so you can redo it quickly:

- `--help` exits before any write — the only safe execution path. Capture it
  as a baseline and diff after.
- Six phases wrap cleanly, verified byte-identical, at these **pre-split**
  line ranges: `resolve_version` 119–138, `download_extension` 139–200,
  `inject_default_config` 201–231, `detect_browsers` 232–257,
  `wire_up_browsers` 348–392, `install_firefox_policy` 393–486.
- Four libs: `leechblock_fetch.sh` (get_latest_tag, resolve_version,
  download_extension), `leechblock_config.sh` (inject_default_config),
  `leechblock_browsers.sh` (**detect_browsers + replace_browser_in_place +
  wire_up_browsers — keep these three together**, see below),
  `leechblock_firefox.sh` (install_firefox_policy).
- **Put `detect_browsers` in the same lib as `wire_up_browsers`.** It writes
  `BROWSERS`/`FIREFOXES`, which `wire_up_browsers` reads; splitting them
  creates a write-only cross-file global and an unfixable SC2034.
- `set -Eeuo pipefail` (note the `-E`) does **not** match
  `extract_shell_functions.py`'s anchor regex, so it will not insert the
  source lines. Add them by hand.
- `get_latest_tag` has three curl fallbacks (releases API → tags API →
  redirect header parse) and is fully testable with a curl shim. Worth 100%:
  a silent failure there installs the wrong version.

### The deployment trap, per file

- **`pacman_wrapper.sh`** — copied to `/usr/local/bin` and the deployed copy is
  preferred on **every pacman invocation**. A naive split breaks `pacman -S` on
  this machine. Re-verify the mechanism (`grep -n "prefer\|deployed"`) before
  assuming. You cannot run `sudo pacman -S` from the Bash tool (deadlocks on
  `db.lck`); hand the user a `! sudo pacman -S <pkg>` line plus the expected
  output if a live check is ever needed. Byte-identical hash equivalence of the
  deployed artifact is accepted as sufficient proof (user's call, Q5).
- **`setup_midnight_shutdown.sh`** — needs a non-standard plan. Its ~39
  top-level-looking functions are NOT all real: several (`log`, `now_epoch`,
  `cmd_add`/`cmd_list`/`cmd_remove`, `require_root`) are duplicated because the
  outer script _generates_ inner standalone scripts via heredocs
  (`create_shutdown_check_script`, `create_override_manager_script`,
  `install_monitor_service`) written to `/usr/local/bin/`.
  `extract_shell_functions.py` and `verify_shell_split.sh` both assume real
  top-level functions and will mishandle a heredoc body. **The plan that
  works:** extract only the genuine outer orchestration functions, treat each
  `create_*_script` heredoc as one atomic unit that moves whole, and verify by
  hashing the _emitted_ `/usr/local/bin/*` content before and after
  (`sha256sum` on a rendered-heredoc temp file), not just by running
  `verify_shell_split.sh` on the outer file.

## The method that worked three times — copy it

Every one of the three completed splits followed this, and it caught real bugs
each time:

1. **Capture a baseline BEFORE any edit.** Either a golden output fixture (if
   the script writes to a directory you control — `generate_study_materials`
   took `$RESULTS_DIR` as `$1`) or, if it writes to hardcoded system paths, a
   `--help`/`--status` run plus `sha256sum` of everything it could touch.
   **Never run an installer to get a baseline** — an aborted run can leave the
   system half-configured. `hosts/install.sh` had no safe mode at all and was
   proven textually only; that is acceptable and was recorded as such.
2. **Wrap top-level blocks into phase functions WITHOUT re-indenting them.**
   `extract_shell_functions.py` only moves functions, and most of these files
   are mostly top-level code. Quoted heredoc terminators must stay at column 0.
   Let `shfmt` indent afterwards.
3. **Prove each wrapped body is byte-identical** to its original line range
   with a Python diff, and check a line-multiset for lost content. This is what
   covers the top-level code that `verify_shell_split.sh` cannot see.
4. **Run `verify_shell_split.sh <pre-rev> <old> <old> <new>...`** — additions
   are your new wrappers; any `-`/`+` pair on the same name is a body you
   changed and must justify.
5. **Re-verify the baseline** after every step, including after `shfmt`.
6. **Then** write tests, fix what they expose, commit.

## Tooling

- `meta/scripts/check_file_length.sh --all` — the gate. Applies to test files
  too; two test files needed splitting twice to stay under it.
- `meta/scripts/extract_shell_functions.py` — moves functions brace-by-brace.
  **Never slice by line range.** Anchors the source line on `set -e`-ish lines;
  `set -Eeuo pipefail` does not match.
- `meta/scripts/verify_shell_split.sh <rev> <old> <new>...` — for a partial
  split, list the old path among the new paths too.
- `meta/scripts/shell_coverage.sh <test> <subject> [min]` — kcov wrapper. Hand
  it the test script **directly**; `bash script.sh` instruments bash and
  reports 0/0. Point it at a `run_all.sh` when several test files jointly cover
  one lib.

## Sharp edges that have bitten (each one cost real time)

- **`shfmt -w` corrupts `[hyphenated-keys]` in associative arrays.** Grep after
  every run. This is what killed the leechblock attempt.
- **A subshell strands state.** `out=$(check_foo)` or `(cd x && check_foo)`
  throws away every global the function set, so assertions silently test
  nothing. Redirect to a file and `cat` it instead.
- **`grep -v` exits 1 when it filters every line**, which kills the caller
  under `set -e`. Use `{ grep -v ... || true; }`.
- **Order matters: `grep -v '^#' file | head -n N`, not `head | grep`** — the
  other way, comment lines count against N.
- **`printf '---...'` parses leading dashes as options.** Use
  `printf '%s' '---'`.
- **A function whose pipeline starts with a failing `grep` aborts under
  `set -o pipefail`** if called bare. Production often escapes this by calling
  it inside `if`, which suppresses `set -e`. Call it via `if` in tests too.
- **`local a="$1" b="${a}"` fails under `set -u`** — separate `local` lines.
- **A function that calls `exit` kills the test script** if called directly in
  an `if` condition. Use a subshell: `if (fn args); then`.
- **New sourced libs need a shebang AND the executable bit**, staged with
  `git add --chmod=+x` — a plain `git add` afterwards resets it. This bit
  every single commit; check `git ls-files -s` for `100755` before committing.
- **SC2034 on a cross-file global is real, not noise** — the hook runs
  shellcheck with no `-x` and genuinely cannot see the reader. Fix it by
  moving the writer next to the reader, or by routing writes through a
  setter/getter in the reader's file. Never suppress.
- **kcov mis-attributes `}` lines closing a `{ ... } >>file` group**, and
  reports them uncovered even when a passing assertion proves the group ran.
  Diagnose it (run the suite _under kcov_ and confirm it still passes) rather
  than chasing it; record it in the evidence.

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, no per-file-ignore without asking
  every time, no new shellcheck disable.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`, **plus a contract** in
  `docs/superpowers/contracts/` (≥4 code files staged — always true here). Put
  the **measured** number in it, not a rounded one.
- **A test file broken by your commit is a same-session bug, not a TODO.** Run
  `gh run list` after every push.
- `pre-commit run --files <changed>` **after** `git add`. `prettier` and
  `ci-mirror` run on **pre-push**. `npx prettier --write` any `.md`/`.json` you
  touch, evidence and contract files included.
- `codespell` runs in pre-commit and rejects some spellings you would not
  expect, including in code comments and test descriptions. It caught one in
  the last session. Fix the wording rather than adding an ignore.
- Work directly on `main`. `git stash` and branch creation are blocked; use
  `git worktree add --detach` for a clean baseline (but NEVER `git filter-repo`
  inside a worktree — it shares the object store).
- Watch `jscpd` (fails above 2%). The test harnesses are the risk: source one
  shared harness per `lib/tests/` dir rather than copying setup blocks.

## Phase 2: Wire the file-length gate into pre-commit

**Do NOT start until Phase 1 exits 0** — wiring it early breaks every commit
repo-wide, including unrelated ones.

1. Add a `local` hook to `.pre-commit-config.yaml` running
   `bash meta/scripts/check_file_length.sh --all`, following the existing
   `language: system` + `pass_filenames: false` shape (see
   `ai-evidence-contract` / `no-polling-antipatterns`). Repo-wide, not
   per-file: a file that grows past 250 lines without being staged this commit
   should still be caught.
2. **GitHub-Actions-green check — GENUINE DESIGN FORK, ask the user first.** A
   pre-commit hook cannot block on "is CI green" for a commit that does not
   exist yet. Two real options:
   - **(a)** check the latest run on `main` is green before allowing a new
     commit — catches "building on a known-broken baseline", not "did MY change
     break it";
   - **(b)** a **pre-push** hook running the CI workflows' local equivalent
     before allowing the push — closer to the real guarantee, and `ci-mirror`
     already does this for the Python/pre-commit side. Extending it to also run
     `Shell tests`' local equivalent is likely the more honest answer.

   This is the one place in Phases 1–2 where stopping to ask is correct.

3. Verify by making a throwaway file exceed 250 lines, confirming the commit is
   blocked with a clear message, then removing it.

## Phase 3: Repo-wide 100% shell coverage gate — largest phase, many sessions

**Do NOT start until Phases 1 AND 2 are done.** Re-count first; it was ~487
`.sh` files repo-wide against a handful of `lib/tests/` dirs.

**Ask the user to confirm scope before starting Phase 3 at all**, and ask
whether the gate should be repo-wide from day one or **ratchet** (only new or
modified files must be covered, with a shrinking allowlist of pre-existing
untested files). A hard repo-wide gate would block unrelated commits to any of
450+ files until every one has tests. Recommend the ratchet, but it is the
user's call.

---

## What the last session finished (do not redo)

Five commits, all pushed, CI green:

| Commit     | What                                                  |
| ---------- | ----------------------------------------------------- |
| `9085a4e5` | `check_and_enable_services.sh` 1225 → 202, eight libs |
| `0a69d183` | Same file: `$SYSROOT` prefix → 100% on 7 of 8 libs    |
| `08f3c764` | Same file: fixed the status-downgrade bug (below)     |
| `241652ca` | `generate_study_materials.sh` 1017 → 148, six libs    |
| `47478791` | `hosts/install.sh` 913 → 150, six libs + a data file  |

### Defects found and fixed (all pre-existing, all verified)

1. **A warning masked an error in 8 places** (`services_units.sh`,
   `services_hosts.sh`). `status="warning"` was assigned unconditionally,
   overwriting an `error` set by an earlier check. In the three unit checks
   this meant `report_and_fix` — which repairs only on `error` — **never ran**,
   so a timer that was both disabled and inactive was reported and then left
   broken. Proven with an A/B: without the guards `status=warning, repair ran
0`; with them `status=error, repair ran 1`.
2. **`generate_study_materials`**: `--top` was silently ignored for imports
   (hardcoded `head -20` in 3 loops); comment lines became flashcards (only 1
   of 9 loops filtered them); `python_doc_url` required a `$2` it never reads,
   which aborted any caller using `set -u`.
3. **`hosts/install.sh`**: `extract_unblock_entries_from_script` matched its
   own `PROTECTED_UNBLOCK_LIST_START`/`_END` markers as if they were domains.
   **They are in this machine's live `/etc/hosts.unblock-entries.state` right
   now.** After the fix the whitelist reads as having shrunk by 2, which the
   guard allows, so the next install self-heals the state — no manual step, but
   the next run will report 2 removed entries.

### Known-good patterns to copy

- `linux_configuration/scripts/periodic_background/lib/tests/` — the fullest
  example: a shared harness, a `services_assert.sh` split out for the cap, a
  `services_path.sh` that owns PATH so `command -v` is controllable, and a
  `run_all.sh` used as the coverage subject.
- `linux_configuration/scripts/periodic_background/hosts/lib/tests/` — how to
  test a script you must never execute: shim `chattr`/`curl`, point the
  already-variable state-file paths at a tmpdir, and add
  `${HOSTS_INSTALL_SCRIPT_PATH:-$0}`-style overrides where a path is otherwise
  underivable.
- `linux_configuration/scripts/periodic_background/hosts/custom_entries.hosts`
  — a ~320-line heredoc turned into a data file, with the guard that reads it
  updated in the same commit and the extracted set diffed (254 domains,
  identical) to prove the guard still sees what it saw before.

### Known tooling bug, fix opportunistically

`~/.claude/scripts/dart_format_changed.sh <repo>` reports "No changed Dart
files" even when files changed, if invoked with a repo path from outside that
repo — it `cd`s into `$repo` then runs `git status --porcelain`, whose paths are
relative to the **git worktree root**, so its `[[ -f $path ]]` check fails for
every file. Workaround: `dart format <files>` directly. Real fix: `cd` to the
git toplevel, or strip the prefix.

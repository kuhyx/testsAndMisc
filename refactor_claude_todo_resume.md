# Resume: enforce the 250-line file cap

> **Paste this whole file to a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Continues `refactor_claude_todo.md`, which is still the
> spec — read it too, but the decisions below override it where they differ.

## Where things stand

**83 files** over 250 lines (was 183). Everything is committed and pushed to
`main` at `093e2f6`; the tree is clean.

**`python_pkg/` is DONE — 50 violations → 0.** Do not reopen it. Cleared one
package per tranche, pushing after each: `brother_printer` (15→0, suite pinned
at 402), `code_tutor` (13→0, 216→217), then `android_ui`, `app_icons`,
`token_audit`, `focus_policy`, `random_jpg` (57/44/81/137/14), then
`wsg_grabber`'s six test modules (277).

**`linux_configuration` is 84 → 42**, in fourteen batches. **All 12 prose files
are done** (8 split, 2 deleted as completed-work records on the user's ruling).
**`kcd2_dice_solver` is 12 → 4**, all four remaining being source files. The
shell pattern is settled and scripted — read `docs/shell-split-recipes.md`
before touching another one.

In TypeScript a bad seam **compiles clean and fails at runtime** — an import
cycle leaves a constant `undefined` at module-init. Always run the suite.

Earlier sessions had already done: the `~/utils` exemptions, the
`no-inline-python` hook, `CLAUDE.md`, `poker-stakes/`, and every `wsg_grabber`
**source** file.

`git log --oneline --grep='cap'` is the authoritative list.

## What is left

| Directory                          | Count        |
| ---------------------------------- | ------------ |
| `linux_configuration`              | 42           |
| `phone_focus_mode`                 | 12 (do LAST) |
| `focus_owner`                      | 11           |
| `billsplit`                        | 6            |
| `meta` / `kcd2_dice_solver`        | 4 each       |
| `reverse_survivors`/`bucket_catch` | 2 each       |

**Four `linux_configuration` files are deliberately over the cap**, all for
one reason: **state crosses the seam.** Pass it explicitly first, then split;
never suppress. See "When to give up on a seam".

| File                                  | Why                                          |
| ------------------------------------- | -------------------------------------------- |
| `check_and_enable_services.sh` (1337) | every `check_*` writes one `SERVICE_STATUS`  |
| `steam_compatibility.sh` (663)        | `CACHE_MAP` written in a lib, read by `main` |
| `diagnose_pacman_hook_stall.sh` (493) | `LAST_ELAPSED` / `PACMAN_BIN` cross the seam |
| `libre_translate.sh` (488)            | ~19 globals cross any seam                   |
| `enforce_vbox_hosts.sh` (443)         | every seam falls inside a heredoc            |
| `clean_audio.sh` (419)                | probe-result globals through two libs        |
| `setup_passwordless_system.sh` (374)  | no `main()`; top-level block kept by hand    |

Same in TypeScript: `kcd2`'s `search.ts` and `badgeValue.ts`, and
`reverse_survivors`' `sim.ts` (`step` ⇄ `survivorStep`) and `types.ts`.

**The pre-commit `shellcheck` hook lints each lib alone**, with no view of the
caller's globals — stricter than `shellcheck -x` on the entry, and the check
that decides whether a seam is real. Run it before believing a split.

Next: the remaining `main()`-shaped shell scripts, then `focus_owner` and
`billsplit` (Kotlin+Dart, untouched so far — check for a test command first).

## The live worklist

Do not work from a list in this file — it goes stale. Run:

```bash
bash ~/utils/scripts/check_file_length.sh --all
```

**Every count here is a snapshot and will be wrong by the time you read it.
Run the script.** The table above tells you where the bulk sits, nothing more.

**Do the source files in a package before its tests.** Proven on `wsg_grabber`
and again on all seven `python_pkg` packages: the test files then split along
seams the source already established, instead of you inventing a new boundary
for them. On `brother_printer` this meant four of the five source splits needed
**no test edit at all**.

## Decisions already made (do not re-ask)

1. **Full clearance** to `--all` exit 0. When context runs out, write a fresh
   handoff like this one rather than stopping mid-way.
2. **CI checks only files in the push/PR range**, not `--all`.
3. `docs/superpowers/plans/**` + `sessions/**` are exempt — already done.
4. `poker-stakes/` is tracked — already done.
5. For prose: automate what can be automated, delete the automated lines, keep
   only HOW, never WHY.
6. Shell verification is `bash -n` + `shellcheck` + `systemctl cat` path checks.
   **Never execute enforcement scripts that mutate the phone or the live system.**
7. One commit per logical unit.
8. **Editing test files to follow moved code is allowed** (2026-08-16), bounded
   by: no assertion changed, nothing deleted/skipped/weakened, and an identical
   pass count before and after. See `docs/python-split-recipes.md`. Do not
   re-ask this — an earlier session wrongly treated tests as untouchable and
   stalled on `brother_printer` because of it.
9. Per-commit gate is `pre-commit run --files <changed>`; the real `git commit`
   is the full gate (it adds jscpd). Push per directory tranche, not per commit.
10. **When a seam splits code covered by a per-file-ignore, fix the lint —
    do not copy the ignore onto the new file** (user's call, 2026-08-16).
    Done for `code_tutor/cli.py`: `S607` fixed with `shutil.which`, `PERF203`
    by extracting the probe so the poll loop carries no `try`/`except`. Both
    entries deleted from `meta/pyproject.toml`; the repo now has two fewer
    suppressions. The `which()` fix added a branch, so a covering test was
    written (216 → 217) rather than excluding it. Expect the same question on
    any remaining per-file-ignore you split through — ask, don't assume.

## The constraint that will bite you

**Wire the file-length gate LAST**, only once `--all` already exits 0.

`meta/scripts/ci_mirror.sh:109` runs `pre-commit run --all-files` as a
**pre-push** hook, and `.github/workflows/pre-commit.yml:105` does the same in
CI. Registering the hook while violations remain makes **every `git push` fail**
until the last file is fixed. Do not scope around it with `exclude:`/`files:` —
that is the allowlist the spec forbids.

Final commit, once and only once the tree is clean:

```yaml
- id: file-length
  name: file length <= 250 lines
  entry: bash /home/kuhy/utils/scripts/check_file_length.sh
  language: system
```

Plus `.github/workflows/file-length.yml` modelled on
`~/todo/.github/workflows/file-length.yml` (checks out `kuhyx/utils` into
`.utils`), scoped to changed files. Then prove it fails: stage a deliberately
251-line file, confirm `git commit` aborts, delete it.

## Language recipes

- `docs/python-split-recipes.md` — the seam-selection rule, the `__all__`
  re-export form, the `TC001` trap, the mixin shape, and the coverage
  behaviour of new sibling modules. `python_pkg` is done; read it if a stray
  `.py` turns up, or for the seam rule, which generalises to any language.
- `docs/shell-split-recipes.md` — **read this before the next
  `linux_configuration` split.** What replaces the pass count when there is no
  test suite, which scripts escape the repo, the lib shape that satisfies both
  shellcheck and the shebang hook, and six traps found the hard way. The
  stubbed-run check is scripted at `meta/scripts/verify_shell_split.sh`; run it
  on every split whose script ends in `main "$@"`.

Each rule in both cost a failed gate run or a revert to establish.

## Split recipes

- **Shell** — extract into `lib/*.sh` sourced by a thin entry script. See
  `docs/shell-split-recipes.md` for the lib shape; note it corrects the old
  advice to repeat `set -euo pipefail` in every lib.
- **Python** — extract cohesive helpers into sibling modules; keep the public
  API stable by re-exporting.
- **TS/Dart** — extract components; re-export from the original path so no
  importer changes.
- **Tests** — split by describe/test-group. Coverage must not drop, and
  **verify by the pass _count_, not a green run**: a split that loses a whole
  module still reports "passed".
  In `python_pkg`, shared fixture builders go in the package's
  **`tests/conftest.py`** — the `name-tests-test` hook rejects any other
  non-`test_*.py` file under `tests/`, so a `_helpers.py` will fail the gate.
  `python_pkg/syncyomi_guard/tests/conftest.py` is the precedent, and
  `meta/pyproject.toml` omits `*/tests/*` from coverage by path so nothing
  there is counted as production code (the opposite of the `poker-stakes`
  trap below). Prefer one shared conftest over another `partN` file: the repo
  already carries four, and each new one that redeclares the same fixture
  scaffolding pushes jscpd toward its 2% duplication threshold — which only
  fires on the real `git commit`.

Never game the cap: no one-lining, no deleting tests, no moving code into an
exempt extension, no suppressions.

## Never edit files while a push is running

`git push` runs pre-commit, which **stashes unstaged changes and restores them
afterwards**. Editing a file in that window makes the restore fail with
`patch does not apply`, and the push aborts — _while `git push | tail` still
reports exit 0_, because the pipe masks it. This cost two silent failed pushes
and one silently reverted split.

Rules that follow:

- Stage (`git add`) before running `pre-commit run --files ...` on a
  work-in-progress tree, or the same stash cycle can revert the edit.
- Push only with a clean tree, and do not start other file edits until it
  returns.
- After any push, confirm with `git status --short --branch` that it does not
  still say `ahead N`. Never trust the exit code alone.

## Traps that cost time in the last session

- **Test fixtures and coverage.** When splitting a test file, shared helpers
  must go where the coverage config already excludes them (in `poker-stakes`
  that is `src/test/**`, matched **by path**). Putting them beside the source
  makes the coverage tool count them as production code and the 100% gate
  fails. Move the file; do **not** add a `coverage.exclude` entry.
- **`end-of-file-fixer` aborts commits.** Files built with `sed`/`cat` often
  lack a trailing newline. The hook fixes it and then fails the commit
  ("files were modified by this hook"). Just `git add` again and re-commit.
- **Formatters silently revert edits.** A PostToolUse formatter stripped an
  added import twice. After editing, `grep` the file to confirm the change
  survived before running anything.
- **Contracts.** Staging **≥4 code files** requires a _fresh_
  `docs/superpowers/contracts/*.json` in that same commit, on top of the
  per-commit `docs/superpowers/evidence/*.json`. Required keys: `title`,
  `objective`, `acceptance_criteria`, `out_of_scope`, `verifier`. Validate with
  `python3 meta/scripts/validate_contract.py <file>`.
- **`invariants.test.ts` in poker-stakes** flakes on its 5s timeout under
  parallel coverage load. It passes standalone in ~2.6s. Not a regression —
  do not "fix" it by weakening the test.
- **Long commands**: background anything over ~60s rather than blocking.

## `phone_focus_mode` — highest blast radius, do it LAST

Two silent failure modes:

1. **`deploy.sh` has a hardcoded flat push list** (search for `adb_cmd push`,
   around lines 374–383) with **no `lib/` subdirectory**. Every new split lib
   must be added there in the same commit, or the phone sources a missing file
   at runtime — gate green, tests green, device broken.
2. **`config.sh` (556 lines) is sourced by 11 scripts.** Keep `config.sh` as
   the entry point that re-sources its own parts, so all 11 callers keep
   working untouched.

Static check after each split: grep `deploy.sh`'s push list and every
`source`/`.` line in `phone_focus_mode/*.sh` and confirm each new lib appears.

## Suggested order

1. The 48 near-misses (251–300) — mechanical, biggest count drop.
2. `python_pkg` (50) — `pytest-coverage` gates each changed package on commit.
3. `linux_configuration` (84) — largest; check systemd unit paths still resolve.
4. `kcd2_dice_solver`, `focus_owner`, `billsplit`, the rest.
5. `phone_focus_mode` (13) — with the guard above.
6. Gate wiring + CI workflow — last.

## Done condition

```bash
cd ~/testsAndMisc && bash ~/utils/scripts/check_file_length.sh --all   # exit 0
pre-commit run --all-files                                             # passes
```

Plus: a staged 251-line file makes `git commit` fail.

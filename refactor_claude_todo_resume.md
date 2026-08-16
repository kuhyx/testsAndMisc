# Resume: enforce the 250-line file cap

> **Paste this whole file to a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Continues `refactor_claude_todo.md`, which is still the
> spec — read it too, but the decisions below override it where they differ.

## Where things stand

**184 files** over 250 lines (was 198). All work so far is committed and pushed
to `main`; the tree is clean. The three unrelated edits an earlier handoff
warned about (`README.md`, the two `analysis_options.yaml`) are no longer
present.

Done already (do not redo):

- `~/utils`: `plans/` + `sessions/` exempted from the cap (`specs/` still capped)
- `17b20e5` new `no-inline-python` pre-commit hook + its one violation
- `004b4b0` `CLAUDE.md` 259 → 141
- `72a5e28` + `73b85f5` `poker-stakes/` tracked, then 4 violations → 0
- `77c6d9f`…`d86965f` **every `wsg_grabber` source file** — `catalog` 251→175,
  `cli` 282→247, `review` 330→196, `net` 335→109, `store` 382→202,
  `downloader` 420→238, `player` 373→235, `ui` 398→242
- `e03fbd1` `wsg_grabber/tests/test_review.py` 297 → 112 + two new modules

`git log --oneline --grep='250-line cap'` is the authoritative list.

## The live worklist

Do not work from a list in this file — it goes stale. Run:

```bash
bash ~/utils/scripts/check_file_length.sh --all
```

**Every count in this file is a snapshot and will be wrong by the time you read
it. Run the script.** As of `ac02a23` the shape was `linux_configuration` 84,
`python_pkg` 41, `phone_focus_mode` 13, `kcd2_dice_solver` 12, `focus_owner`
11, `billsplit` 6, `reverse_survivors`/`meta`/`docs` 4 each,
`.github`/`bucket_catch` 2 each — quoted only to tell you where the bulk sits,
never to work from.

Within `python_pkg`: `brother_printer` 15, `code_tutor` 13, `wsg_grabber` 6
(tests only), then singles.

**Do the source files in a package before its tests.** Proven on `wsg_grabber`:
the test files then split along seams the source already established, instead
of you inventing a new boundary for them.

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

## Python split recipes

`docs/python-split-recipes.md` holds the settled Python rules: the `__all__`
re-export form, the `TC001` trap that lints clean and breaks at runtime, the
mixin shape for splitting a class, what the tests pin in place, and the
coverage behaviour of new sibling modules. **Read it before the first Python
split** — each rule there cost a failed gate run or a revert to establish.

## Split recipes

- **Shell** — extract into `lib/*.sh` sourced by a thin entry script,
  `set -euo pipefail` in each. Follow `phone_focus_mode/lib/` and
  `linux_configuration/scripts/lib/common.sh`.
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

# Next session: keep splitting, tests first

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## Where things stand

Over-cap: **41 → 37** (29 shell, 4 python, 2 kotlin, 1 dart, 1 markdown — the
markdown is this file). 12 commits, `6713ef3..ff1a1b6`, all pushed.

The C++ category is empty and the `system-maintenance/bin/` python is done:
every module there is under the cap at 100% line+branch coverage.

## The method, which worked six times

1. **Measure coverage of the block you intend to move, first.** The failure
   this catches is real: `_usage_report_parsing.py` was 39% covered and the
   uncovered 61% was almost exactly the half a split would extract. Splitting
   that first would have proved nothing.
2. **Tests land in their own commit, before the split.** Not negotiable — a
   split verified by tests written alongside it is verified against the
   post-split shape.
3. **Move code verbatim, then prove it.** Write a throwaway script that parses
   HEAD and the new modules with `ast`, normalises each top-level def through
   `ast.dump(ast.parse(ast.unparse(node)))`, and asserts identity. It caught a
   literal `×` typed where the original had a `×` escape. Formatting-blind,
   logic-sensitive; ~40 lines, worth rewriting each time.
4. **Rewrite import sites to name the owning module.** No re-export barrels.
   Check the _whole_ graph: one split shipped with `usage_report.py` still
   importing `_fmt_h` through the render module, and the commit message claimed
   otherwise.
5. **Run the actual program.** Every unit test here stubs subprocesses, so only
   a real run proves the import graph resolves. Run every entry point the split
   touched, not just one.
6. Re-run every gate, commit one split at a time, with evidence.

## Traps that cost time this session, in order of cost

- **`monkeypatch.setattr` must target the module whose namespace resolves the
  name** — the caller's, not the one the function moved to. Getting this wrong
  on `_run_since` made `main()` call the real function, which read the
  machine's actual atop logs and **hung the suite** rather than failing. If a
  pytest run stalls after a split, this is why.
- **Splitting a test file can put it over the cap.** Two commits added
  over-cap files while fixing something else (`DropZone.test.tsx` 250 → 256 on
  a lint fix; two new test files at 373 and 272). Check
  `check_file_length.sh --all` _before_ committing, not after.
- **Don't move too much at once.** The `usage_report.py` split needed two
  functions relocated after their first placement made an import cycle, plus
  four modules' worth of patch targets re-pointed. Smaller slices are cheaper.
- **`TYPE_CHECKING` imports bite when code moves.** `Path`, `_fmt_h` and
  `dataclass` each ended up importable only for type checking while used at
  runtime. All three failed at first call; 100% coverage surfaced them at once.
- **A backgrounded `git push | tail` hides failure.** One push reported exit 0
  while printing `error: failed to push some refs`. Verify with
  `git status -sb` showing no `[ahead N]`.

## What to do next

### 1. `meta/scripts/optimize_vscode.py` (498, untested)

The largest remaining python file and completely uncovered. Same recipe:
coverage commit, then split. Take a **smaller first slice** than the last one.

### 2. The three `transcribe_*` files (356 / 302 / 289, untested)

`linux_configuration/scripts/single_use/misc/testsAndMisc-bash/tools/`.
`_transcribe_diarize.py`, `transcribe_fw.py`, `transcribe_helpers.py`. Check
whether they import heavy ML deps at module scope — if so, testing them needs
the import stubbed, and `python-mpv`-style "loads a native lib at import" is a
known CI-breaker in this repo.

### 3. Shell, where the remaining 29 are

`docs/shell-split-verification.md` has the harness. Two named blockers:

**Scripts copied to a system location and run from there.**
`install_leechblock.sh` (485) is copied to `/usr/local/share/digital_wellbeing/`
and `pacman_wrapper.sh:831` prefers that deployed copy on **every pacman
invocation**. Split the repo copy into an entry that sources `lib/`, and the
deployed copy — which has no `lib/` beside it — dies on its first `source`.
Every `pacman -S` on this machine then fails. The trace harness cannot see
this: it runs the repo copy, where `lib/` exists. Same for
`block_compulsive_opening.sh` (705), whose `install_all` copies the running
script into `/usr/local/bin`. **Teach the installer to deploy `lib/` first, in
its own commit, then re-baseline its manifest, then split.**

**Source-text tests.** `test_pacman_wrapper_security.sh` asserts things like
`grep -q 'source .*pacman_lock_lib.sh' pacman_wrapper.sh`. It **is** in CI
(`.github/workflows/shell-tests.yml`, the `arch-tests` list). Rewriting those
assertions is authorised, but the replacement must prove the same property of
the split whole — grep across entry **and** libs, or better, source the library
and assert the behaviour. State in the evidence how the new assertion is at
least as strong.

`nvidia_troubleshoot.sh` (336) has a different blocker: its trace dies at step 3
because `backup_file` writes into an unbound `/etc`, so 239 of 336 lines never
execute under the harness.

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, `# type: ignore`, `eslint-disable`,
  `# shellcheck disable`, no lowered coverage threshold. Several were tempted
  this session; all were resolved by changing the code. If a split seems to
  need one, the seam is wrong.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (copy `template.json`).
  Staging **≥4 code files also needs** a fresh `docs/superpowers/contracts/*.json`.
  Validate both with `meta/scripts/validate_{evidence,contract}.py`.
- `pre-commit run --files <changed>` before committing. **`prettier` and
  `ci-mirror` run on pre-push, not pre-commit** — a commit can pass and the push
  still fail. Run `npx prettier --write` on any `.md` you touch, including this one.
- Work directly on `main`. `git stash` and branch creation are blocked by hooks.
- **Do not wire the file-length pre-commit hook.** It lands last, once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0. 37 files are still over.
- Cap pytest memory: `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0`.
- New sourced shell libs: shebang **and** the executable bit, sourced via
  `"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"`, with
  `# shellcheck source=<name>.sh` relative to the script's own directory.

## Known pre-existing state — not yours, do not fix silently

- **`bucket_catch/packages/frontend` has 4 eslint errors** (was 45). Each is
  documented with measured reasoning in
  `docs/superpowers/evidence/bucket-catch-eslint-2026-08-17.json`. The one worth
  knowing: `usePuzzleGameLoop.ts:129`'s `Map.get(...)!` cannot be fixed with
  `?? Infinity` — that was tried and measured at 219 branches / 99.54%, because
  the default side is unreachable. Trading a lint error for a coverage failure
  is not a fix. `npm run coverage` is green: 145 tests, 100%.
- `bash linux_configuration/tests/test_security_hardening.sh` exits 1 with one
  failure, `❌ FAIL: Compulsive block wrappers installed`. It belongs to
  `block_compulsive_opening.sh`.
- `_compute_window` in `_usage_report_run.py` is dead: documented as "kept for
  backwards import compatibility", zero callers anywhere (verified by grep over
  `.py` and `.sh`). It is tested, so deleting it is safe and cheap.
- Repo-wide `jscpd` reports ~2.5% from the working tree but 1.47% at HEAD in a
  clean worktree — the excess is vendored `.venv` site-packages. Don't chase it.

## Testing notes specific to this repo

- `linux_configuration/tests` **is** in CI, but never by name: `pyproject.toml`
  sets `testpaths`, so the bare `pytest` in `python-tests.yml` collects it, and
  `meta/scripts/pytest_changed_packages.py` hard-codes the directory into the
  pre-commit hook. Behaviour is gated; coverage is not (`--cov=python_pkg` only).
  A broken split of these files **does** break the build.
- `name-tests-test` requires every `.py` under `tests/` to be named `test_*.py`,
  including in subdirectories. A shared helper module there is not possible
  without a hook exclusion; put helpers in `conftest.py` or in the one file that
  needs them.
- For a **test-file** split the discriminating check is the test **count**, not
  a green run: a file outside the runner's glob is silently never collected.
- `phone_focus_mode`'s shell tests are **not** in CI. `shell-tests.yml` uses an
  explicit file list covering `linux_configuration/tests/` only.
- `focus_owner` gradle needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and
  `--rerun-tasks`; a plain `gradlew test` reports `UP-TO-DATE` and proves nothing.

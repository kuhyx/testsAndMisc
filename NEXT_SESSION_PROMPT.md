# Next session: shell splits, tests first

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## Where things stand

Over-cap: **37 → 25** (21 shell, 2 kotlin, 1 dart, 1 markdown — the markdown is
this file). 15 commits, `0cf487b..HEAD`, all pushed.

**Python is done.** Every `.py` in the repo is under the cap, at 100% line and
branch coverage where the gate measures it. The remaining work is shell, plus
three files in other languages.

## Tooling built last session — use it, don't rebuild it

Two scripts do the mechanical half. Both were validated before use; don't
re-derive them.

**`meta/scripts/extract_shell_functions.py`** moves functions into a library:

```bash
python3 meta/scripts/extract_shell_functions.py <script> <lib> \
  --functions name1,name2 --header '#!/usr/bin/env bash
# What this library is for.'
```

It walks the file brace-by-brace and lifts only function blocks. **Do not slice
by line range** — these scripts interleave top-level commands between their
function definitions, and a range slice sweeps those into the library, where
they run at source time and in the wrong order. That failure cost a rebuild on
`fresh-install/main.sh`; sourcing the bad version blocked on a sudo password
prompt, which is how it surfaced.

**`meta/scripts/verify_shell_split.sh`** proves the move was verbatim:

```bash
bash meta/scripts/verify_shell_split.sh HEAD <old-path> <new-path>...
# IDENTICAL: all N top-level functions moved verbatim
```

It normalises each function through `shfmt -mn` and compares hashes, so it sees
through reformatting but catches a one-character logic change, naming the
function that differs. **Run it again after pre-commit autofixes** — it caught
`export` edits that lint had accepted but that changed two function bodies.

## The rule that decides where a shell seam can fall

**A file must not assign a global it never reads.** That is SC2034, the repo
forbids suppressions, and the pre-commit hook runs `shellcheck` with **no
`-x`**, so a `# shellcheck source=` directive will not make the checker follow
the link. Each file has to stand alone.

The precedent at `install_pacman_wrapper.sh:29` is about _definitions-only_
libs. It does **not** mean "assignments stay in the entry script" — it means
writer and readers must sit in the same file. `steam_compatibility.sh` split
cleanly only after `detect_system` moved next to `score_game`, and
`load_cache_map` next to `main`.

This is the shell analogue of the `monkeypatch.setattr` trap: the question is
always which file's namespace owns the name. Check with `shellcheck <lib>`
standalone before committing.

## Deployment triage — the trap the trace harness cannot see

`docs/shell-split-verification.md` has the full table. The load-bearing part:

- **`phone_focus_mode/*` (8 over-cap scripts)** — `deploy.sh` copies a
  **hardcoded per-file list** into `/data/local/tmp/focus_mode` and **never
  deploys `lib/`**. A new sibling must be added to that list in the same
  commit, or focus mode dies on the phone at its first `source`. These scripts
  source only `config.sh`, which is on the list, so a **sibling-file** seam
  works and an **entry+`lib/`** seam does not.
- **`install_leechblock.sh` (485), `block_compulsive_opening.sh` (705)** —
  copied to `/usr/local/…`, and `pacman_wrapper.sh:831` prefers the deployed
  copy on **every pacman invocation**. Teach the installer to deploy the
  directory first, in its own commit, then re-baseline, then split. Highest
  blast radius — do these last.
- **The rest** — no deployed copy; entry+`lib/` is safe.

## What to do next, cheapest first

The gate counts **files**, so prefer many small wins over one 1734-line monster.

1. **`generate_study_materials.sh` (1017)**, **`check_and_enable_services.sh`
   (1301)**, **`setup_night_lockdown.sh` (918)**, **`setup_midnight_shutdown.sh`
   (1734)** — big but no deployed copy. Expect 4–6 libraries each; group by the
   state each function touches, per the rule above.
2. **`phone_focus_mode`**: `tether_enforcer.sh` (267) is 17 lines over and the
   cheapest file left anywhere. Then `dns_enforcer.sh` (325), `phone_backup.sh`
   (333), `curfew_enforcer.sh` (367). **Add every new sibling to `deploy.sh`'s
   copy list in the same commit.** `deploy.sh` itself (833) is over-cap too, and
   is not deployed, so it can take an entry+`lib/` shape.
3. **The two Kotlin files** (`EnforcementRunner.kt` 564,
   `DevicePolicyBridge.kt` 415) and **`status_page_state.dart` (307)**. Gradle
   needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and `--rerun-tasks`; a plain
   `gradlew test` reports `UP-TO-DATE` and proves nothing.
4. **The pacman pair**, last, per the triage above.

### Parked, with reasons

- **`libre_translate.sh` (488)** — after its clean seams are taken, `parse_args`
  (111 lines), `write_env_file`, `detect_container_user` and `main` all assign
  **and** read the same configuration globals. Getting the entry under the cap
  needs `parse_args` restructured, not relocated — a refactor, not a verbatim
  move. Four attempts were spent here; don't repeat them without a test first.
- **`diagnose_pacman_hook_stall.sh` (493)** — same shape. `run_one` writes
  `LAST_ELAPSED`, which `main` reads; keeping them together leaves the entry at 292. Also emits SC2153 (`PACMAN_BIN` vs `PACMAN_PID`) once split.
- **`install_plagiarism_tools.sh` (534)** — only 3 tiny functions and ~500 lines
  of top-level code. Nothing to move; needs restructuring.

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, `# type: ignore`, `# shellcheck
disable`, no lowered coverage threshold. If a split seems to need one, the
  seam is wrong — that was true every time it came up last session.
- **Run the actual script.** `steam_compatibility.sh --help` printing usage and
  exiting 0 is what proved four source lines resolved; no static check shows
  that. For scripts too dangerous to run (`main.sh` installs packages,
  `setup_passwordless_system.sh` writes sudoers), say so and rely on `bash -n`
  plus sourcing each library in a subshell to prove it has no side effects.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (copy `template.json`).
  Staging **≥4 code files also needs** a fresh
  `docs/superpowers/contracts/*.json`. Validate both with
  `meta/scripts/validate_{evidence,contract}.py`.
- **Check `check_file_length.sh --all` _before_ committing.** A split that fixes
  one file while pushing a new library over the cap is a net zero.
- New sourced libs: shebang **and** the executable bit. The
  `check-shebang-scripts-are-executable` hook reads the **git index**, so stage
  the mode with `git add --chmod=+x`.
- `pre-commit run --files <changed>` before committing. **`prettier` and
  `ci-mirror` run on pre-push, not pre-commit.** Run `npx prettier --write` on
  any `.md` you touch, including this one.
- Work directly on `main`. `git stash` and branch creation are blocked by hooks.
- **Do not wire the file-length pre-commit hook.** It lands last, once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0. 25 files are still
  over.
- Cap pytest memory: `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0`.

## Known pre-existing state — not yours, do not fix silently

- **`python_pkg/vscode_optimizer` has a real bug, pinned by a strict xfail.**
  `_VENDOR_KW` maps `"ati" → "AMD"`, and `"ati"` is a substring of `"VGA
compATIble controller"`, which appears in **every** `lspci` display line. So
  the `"intel"` key is unreachable and Intel iGPUs are reported as AMD, which
  switches on the GPU-accelerated terminal and AMD-only Electron flags. This
  machine is unaffected only because `"nvidia"` is checked first. The xfail is
  `strict=True`, so fixing the bug without removing the marker fails the suite.
  **The user has been told and has not yet decided.**
- `bash linux_configuration/tests/test_security_hardening.sh` exits 1 with one
  failure, `❌ FAIL: Compulsive block wrappers installed`. It belongs to
  `block_compulsive_opening.sh`.
- **`bucket_catch/packages/frontend` has 4 eslint errors.** Documented with
  measured reasoning in
  `docs/superpowers/evidence/bucket-catch-eslint-2026-08-17.json`. Notably
  `usePuzzleGameLoop.ts:129`'s `Map.get(...)!` cannot be fixed with
  `?? Infinity` — that was tried and measured at 99.54% coverage, because the
  default side is unreachable. `npm run coverage` is green: 145 tests, 100%.
- Repo-wide `jscpd` reports ~2.5% from the working tree but 1.47% at HEAD in a
  clean worktree — the excess is vendored `.venv` site-packages. Don't chase it.

## Testing notes specific to this repo

- `linux_configuration/tests` **is** in CI, but never by name: `pyproject.toml`
  sets `testpaths`, so the bare `pytest` in `python-tests.yml` collects it.
  Behaviour is gated; coverage is not (`--cov=python_pkg` only).
- **Non-`python_pkg` modules are tested via `linux_configuration/tests/`**,
  whose `conftest.py` puts standalone script directories on `sys.path`. Add a
  directory there rather than moving code into `python_pkg/` — that move drags
  the file under a `fail_under = 100` gate and, for anything with a by-path
  caller, breaks it.
- `name-tests-test` requires every `.py` under `tests/` to be named `test_*.py`.
  Shared helpers go in `conftest.py`, exposed as **fixtures** — `conftest` is
  not importable by module name.
- For a **test-file** split the discriminating check is the test **count**, not
  a green run: a file outside the runner's glob is silently never collected.
  That caught a real breakage last session when a move separated a test from
  its doubles.
- `phone_focus_mode`'s shell tests are **not** in CI. `shell-tests.yml` uses an
  explicit file list covering `linux_configuration/tests/` only — so splitting a
  script that **is** on that list means deciding whether the list grows or the
  test sources the library.
- `python_pkg/focus_policy/loader.py` parses `phone_focus_mode/config.sh`.
  Splitting that config breaks the loader unless the parser follows; its 100%
  tests will catch it, but plan the two together.

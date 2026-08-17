# Next session: write the missing tests, then split what they cover

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## Why this brief is different

The previous session split 16 files across kcd2_dice_solver, reverse_survivors,
bucket_catch, focus_owner, phone_focus_mode, linux_configuration and docs. It
took the over-cap count from 51 to 40. Every one of those splits was verified by
a test suite that already existed.

Then it **stopped**, because the remaining files fall into three buckets and
none of them can be split honestly without doing something else first:

1. no test coverage of the code that would move,
2. tests that assert on the file's **source text**, so a split breaks them,
3. generated platform scaffolding that should not be edited at all.

The user has now explicitly authorised all three: **write the tests**, **change
the source-text tests**, and **delete the generated scaffolding**. That is this
session's job, in that order of value.

## The job, in priority order

### 1. Delete `billsplit/windows/` (and decide about `macos/`, `ios/`)

`billsplit/windows/runner/win32_window.cpp` is 288 lines and over the cap. It is
Flutter-generated Windows runner boilerplate — the previous session refused to
split it because `flutter create` regenerates it and hand-editing it is
pointless. The user's answer: **the Windows target is not wanted, so remove it
rather than work around it.**

This is not a one-line `git rm`. Three other places know about that directory:

- `.gitignore` lines ~404-405 carry `!billsplit/windows/runner/resources/app_icon.ico`
  and `!billsplit/windows/runner/runner.exe.manifest` un-ignore rules (the repo
  blocks binaries by default; these are the exceptions that let the Windows icon
  be committed).
- `billsplit/analysis_options.yaml:9` excludes `windows/**` from analysis.
- `.binary-allowlist` may list the icon — check it.

So: remove the directory, remove those three hooks into it, and add
`billsplit/windows/` to `.gitignore` so `flutter create`/`flutter build` cannot
silently resurrect it as an untracked-then-committed directory.

**Ask the user before widening scope:** `billsplit/macos/` (28 tracked files)
and `billsplit/ios/` (40) are the same kind of unused scaffolding, and
`billsplit/linux/` (10) may or may not be in use. The user only named Windows.
Do Windows, then ask whether macOS/iOS should follow — do not assume.

**Verify:** `cd billsplit && flutter analyze` (expect no new issues) and
`flutter test` (expect the existing suite to pass unchanged). The billsplit CI
workflow is `.github/workflows/billsplit-ci.yml` — read what it builds before
you delete anything, and confirm it does not build Windows.

**Done:** `win32_window.cpp` gone from `check_file_length.sh --all`, `flutter
analyze` and `flutter test` clean, and a fresh `flutter create .` in that
directory would not re-add a tracked `windows/`.

### 2. Write tests for the Python that has none, then split it

These are over the cap and were rejected last session purely on coverage.
Measured with
`pytest linux_configuration/tests/test_usage_report_*.py --cov=<the bin dir>`:

| File                       | Lines | Coverage today |
| -------------------------- | ----- | -------------- |
| `_usage_report_parsing.py` | 425   | 39%            |
| `usage_report.py`          | 425   | 47%            |
| `_usage_report_render.py`  | 310   | **21%**        |

They live in
`linux_configuration/scripts/periodic_background/system-maintenance/bin/`.
Their existing tests are `linux_configuration/tests/test_usage_report_since.py`,
`test_usage_report_merge.py`, `test_usage_report_modes.py` (30 tests total, all
passing — the previous session split that one 480-line test file three ways).

**The order matters and is not negotiable:** raise coverage on the block you
intend to move **first**, in its own commit, then split in a second commit. A
split verified by tests written in the same commit proves nothing, because the
tests were written against the post-split shape.

Start with `_usage_report_render.py` at 21% — it is the smallest (310, over by 60) and the most under-tested, so it has the best ratio of test-writing effort
to lines freed. Rendering functions take data and return strings; they are the
easiest thing in this list to test.

Note: **coverage on these files is not enforced by any gate.** `meta/pyproject.toml`
sets `source = ["python_pkg"]`, so these `linux_configuration` scripts are
outside the 100% bar. You are raising coverage because it is the only way to
make a split verifiable, not because a hook demands it.

Also over the cap and completely untested — same treatment, lower priority:

- `meta/scripts/optimize_vscode.py` (498)
- `linux_configuration/.../tools/_transcribe_diarize.py` (356)
- `linux_configuration/.../tools/transcribe_fw.py` (302)
- `linux_configuration/.../tools/transcribe_helpers.py` (289)

### 3. The shell files whose tests grep their source text

The user has authorised changing these tests. The clearest case:

`linux_configuration/scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh`
(929 lines, over by 679) is covered by
`linux_configuration/tests/test_pacman_wrapper_security.sh`, which asserts
things like `grep -q 'source .*pacman_lock_lib.sh' "$WRAPPER_DIR/pacman_wrapper.sh"`.
Move a line into a lib and that assertion fails — by design, since its whole
purpose is "this security-relevant line is present in this file".

**When you rewrite such an assertion, it must not get weaker.** The current test
proves a specific line exists in a specific file. The replacement must prove the
same property of the split whole — e.g. grep across the entry **and** its libs,
or better, source the library and assert the behaviour. Do not simply delete the
assertion or relax it to a pattern that would also match a broken split. State
in the evidence exactly how the new assertion is at least as strong.

`test_pacman_wrapper_security.sh` **is** in CI
(`.github/workflows/shell-tests.yml`, the second list, alongside
`test_hosts_guard_pacman_integration.sh`), so breaking it breaks the build.
Run it before and after.

### 4. What is genuinely blocked, and what "blocked" means

The user asked what "the brief measured and blocked seven by name" meant. Here
it is in plain terms. Four shell scripts cannot be split into an
entry + `lib/` shape for one shared reason, and it is not a testing problem:

**These scripts are copied to a system location and run from there.**
`install_leechblock.sh` is copied to `/usr/local/share/digital_wellbeing/`
(verify: `ls -la /usr/local/share/digital_wellbeing/` — a root-owned copy is
there right now), and `pacman_wrapper.sh:831` prefers that deployed copy on
**every pacman invocation**. Split the repo copy into an entry that does
`source "$SCRIPT_DIR/lib/foo.sh"`, and the deployed copy — which has no `lib/`
next to it — dies on its first `source` line. Every `pacman -S` on this machine
then fails.

The trace harness cannot see this, because it runs the repo copy where `lib/`
does exist. That is why "it traced green" is not evidence here.

Affected: `install_leechblock.sh` (485), `block_compulsive_opening.sh` (705,
`install_all` copies the running script into `/usr/local/bin`).

**Splitting these is a two-file job**: first teach the installer to deploy
`lib/` alongside the entry, then re-baseline the installer's manifest, then
split. That is a legitimate task — it is just bigger than a split, and it must
be done in that order or you break pacman on the user's live machine.

Separately, `nvidia_troubleshoot.sh` (336) has a different blocker: its trace
dies at step 3 because `backup_file` writes `/etc/profile.backup.<stamp>` into
unbound `/etc`, so 239 of its 336 lines never execute under the harness.
Keeping only proven lines in the entry still leaves ~265 — over the cap. It
needs either a better harness or hand-verification.

`check_and_enable_services.sh` (1301), `steam_compatibility.sh` (663),
`libre_translate.sh` (488), `enforce_vbox_hosts.sh` (443) have their own named
blockers in `refactor_claude_todo_resume.md`.

**None of this is "do not touch".** It is "here is the specific thing that will
break, and the order you must do it in". If you take one of these on, the
deploy-`lib/`-first step is the whole task.

## The method (unchanged, it worked 16 times)

1. **Measure coverage of the code you intend to move, before choosing a seam.**
   File-level percentage is a starting point, not the answer — the question is
   whether the tests reach _the block you are moving_. A file at 56% whose
   covered half is exactly what you extract is a fine target; a file at 65%
   whose uncovered lines are precisely the extraction is not.
2. **Capture every gate at HEAD first.** Tests, coverage totals, lint, build.
   Note the _totals_ (e.g. `863/375/181/810`), not just "100%" — unchanged
   totals prove no statement left test reach.
3. Move code **verbatim**. If totals shift, you should be able to name the
   added function.
4. **Rewrite import sites to name the owning module.** No re-export barrels —
   the user asked for this explicitly last session.
5. Re-run every gate. Commit one file's split at a time, with evidence.

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, `# type: ignore`, `eslint-disable`,
  `@ts-ignore`, `# shellcheck disable`, no lowering a coverage threshold. Two
  splits last session tempted one; both were fixed by changing the code
  instead. If a split seems to need one, the seam is wrong.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (copy `template.json`).
  `validate_evidence.py` rejects empty `verification[]` and "should work" /
  "probably fine" / "seems right". **Staging ≥4 code files additionally needs a
  fresh `docs/superpowers/contracts/*.json`** — validate with
  `python3 meta/scripts/validate_contract.py <file>`.
- `pre-commit run --files <changed>` before committing. Note **`prettier` and
  `ci-mirror` run on pre-push, not pre-commit** — a commit can pass and the
  push still fail on markdown formatting. Run `npx prettier --write` on any
  `.md` you touch.
- Work directly on `main`. `git stash` and branch creation are blocked by hooks.
  `git push` runs `ci-mirror` and takes minutes — background it and **do not
  edit files while it runs**.
- **Do not wire the file-length pre-commit hook.** It lands last, only once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0. 40 files are still
  over.
- New sourced shell libs: match the sibling convention (shebang **and** the
  executable bit — a `chmod 755` was needed last session), source them via
  `"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"`, and write
  `# shellcheck source=<name>.sh` relative to the script's own directory
  (`.shellcheckrc` sets `source-path=SCRIPTDIR`).
- Python fixtures go where coverage excludes them; check `[tool.coverage]` in
  `meta/pyproject.toml` before placing one.

## Known pre-existing failures — not yours, do not fix silently

- **`bucket_catch/packages/frontend` has 45 eslint errors.** `npm run lint`
  exits 1. These were _unmasked_, not caused, by a fix last session: `lint` is
  `tsc --noEmit && eslint src`, and a broken `tsc` had been short-circuiting the
  `&&` so eslint had never run on that package at all. 18
  `no-non-null-assertion`, 10 `unbound-method`, 9
  `non-nullable-type-assertion-style`, 5 `no-unnecessary-type-assertion`, plus
  `require-await`, `no-this-alias`, `no-deprecated`. Fixing them needs per-site
  judgment and the user's no-suppressions rule means **asking first**. `npm run
build` and `npm run coverage` there are green (145 tests, 100%).
- `bash linux_configuration/tests/test_security_hardening.sh` exits 1 with
  exactly one failure, `❌ FAIL: Compulsive block wrappers installed`. It
  belongs to `block_compulsive_opening.sh`.
- Repo-wide `jscpd` reports ~2.5% from the working tree but 1.47% at HEAD in a
  clean worktree — the excess is vendored `.venv` site-packages. Don't chase it.

## Testing notes specific to this repo

- **Cap pytest memory**: run it under
  `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0`. A reader
  thread on an unconfigured `MagicMock` once ate 21 GB and OOM-killed the box.
- `focus_owner` gradle needs JDK 21: prefix every `gradlew` call with
  `JAVA_HOME=/usr/lib/jvm/java-21-openjdk`. And use `--rerun-tasks` — a plain
  `gradlew test` reports `UP-TO-DATE` and proves nothing.
- `phone_focus_mode`'s shell tests are **not in CI**. `shell-tests.yml` uses an
  explicit file list covering `linux_configuration/tests/` only. If you add a
  test file there expecting CI to run it, add it to that list too.
- For a **test-file** split, the discriminating check is the test **count**
  (and file count), not a green run: a new file whose name falls outside the
  runner's glob is silently never collected and everything still passes.

## Where the previous session left off

16 commits, `bb9b162..113cada`, all pushed and verified. Over-cap: 51 → 40
(29 shell, 7 python, 2 kotlin, 1 dart, 1 cpp).

Split and verified: all four `kcd2_dice_solver` files; `reverse_survivors`
`sim.ts` + `types.ts`; `bucket_catch` `usePuzzleGameLoop.ts` + its test file
(plus the typecheck repair); `focus_owner` `EnforcementDecision.kt` +
`FocusPolicy.kt`; `phone_focus_mode` `adb_common.sh` + its test file;
`linux_configuration` `atop_agg.c` + `test_usage_report_since.py`;
`docs/shell-split-verification.md`.

Two lessons worth carrying:

- **Measure, don't assume.** `atop_agg.c` was written off as untestable C; its
  Makefile had `test` and `coverage` targets all along and it turned out to be
  the best-covered file left (92.9% lines / 100% functions).
- **A declaration-name scan undercounts.** `FocusPolicy.parse` looked untested
  by name but every test fixture goes through it. Ask "do the tests reach this
  block", not "is this identifier mentioned in a test file".

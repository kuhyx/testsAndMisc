# Next session: §3's second restructure — libre_translate.sh

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

Over-cap: **14** (12 shell, 2 kotlin, 1 dart). Working tree clean, `main` in
sync as of commit `071d706`.

Two standing decisions from the user, already made — do **not** re-litigate:

1. **100% line coverage on what you extract** — same bar as the previous
   session applied to `install_plagiarism_tools.sh`.
2. **Split blind where there is no device.** Do not deploy to the phone, do
   not ask to. Prove splits with tests, hashes and real runs instead.

---

## 0. What just happened (read this, don't repeat it)

The previous session's brief listed three §3 restructures. The first,
`install_plagiarism_tools.sh`, was split (534→94 lines + 3 libs, 100%
coverage via a PATH-shim test harness, verified against a real venv with
actual nltk/scikit-learn) — then the user said they no longer use the
plagiarism tools at all. The whole thing (install script + 2 extracted Python
files + 3 libs + 5 test files, 13 files total) was moved to
`kuhyx/testsAndMisc-archive` with full git history preserved via
`git filter-repo`, and deleted from this repo. See commits `2a7b9d9` (the
split) and `071d706` (the archival) for the full mechanics if you need the
`git filter-repo` recipe again for something else — it is not expected to
recur this session.

**Lesson for this session:** before sinking real effort into a split, it may
be worth a one-line check-in — "do you still use this?" — for anything that
looks like it could be dead code, especially in `single_use/` directories.
Not a blocking gate, just don't be surprised if the answer changes scope.

## 1. This session's task: `libre_translate.sh` (488 lines, 18 functions)

Location: `linux_configuration/scripts/single_use/misc/testsAndMisc-bash/libre_translate.sh`

**The user already chose the approach** (from the original brief, still
valid): move the whole config-globals cluster into **one lib that owns both
the writes and the reads**. Do not try relocating `parse_args` alone — four
attempts at that failed in an earlier session. Read the file fully before
planning the split; it has real functions already (unlike
`install_plagiarism_tools.sh`, which had almost none), so
`meta/scripts/extract_shell_functions.py` and
`meta/scripts/verify_shell_split.sh` are the right tools here — they were
mostly _inapplicable_ to the plagiarism installer because it lacked function
structure, but this file has 18 functions and should fit their intended use
case.

**Before you start**, confirm scope hasn't drifted: `git status --short` and
`wc -l` on the target file, same as the check that caught the plagiarism
tools were unused this time — it's cheap insurance.

## 2. Also outstanding in §3

`diagnose_pacman_hook_stall.sh` (493 lines, 15 functions) —
`linux_configuration/scripts/single_use/fixes/diagnose_pacman_hook_stall.sh`.
`run_one` writes `LAST_ELAPSED`, `main` reads it — that global crosses the
split seam deliberately (see the SC2034 rule in §5 below), so it must stay in
whichever file both functions land in, or get passed explicitly. Emits
**SC2153** (`PACMAN_BIN` vs `PACMAN_PID`) once split — a real finding to
resolve, never to suppress. Do `libre_translate.sh` first; this one waits its
turn.

## 3. §4 — do not touch this session

`install_leechblock.sh` (485) and `block_compulsive_opening.sh` (705) are
copied to `/usr/local/…`, and `pacman_wrapper.sh:831` prefers the deployed
copy on **every pacman invocation**. Splitting them naively breaks every
`pacman -S` on this machine. Out of scope until `libre_translate.sh` and
`diagnose_pacman_hook_stall.sh` are both done and the user explicitly says to
continue into §4.

You cannot run `sudo pacman -S` from the Bash tool — it deadlocks on
`db.lck`. Hand the user a `! sudo pacman -S <pkg>` line plus the expected
output if `pacman_wrapper.sh` ever needs live verification.

## 4. Out of scope until the user says otherwise

`setup_midnight_shutdown.sh` (1734), `check_and_enable_services.sh` (1301),
`generate_study_materials.sh` (1017), `pacman_wrapper.sh` (929),
`setup_night_lockdown.sh` (918), `hosts/install.sh` (912),
`setup_hosts_guard.sh` (576), `EnforcementRunner.kt` (564),
`DevicePolicyBridge.kt` (415), `status_page_state.dart` (307) — check
`check_file_length.sh --all` for the current exact list before assuming this
is still accurate, since files change size between sessions.

`pacman_wrapper.sh` carries the same live-deployment trap as §3/§4. The
Kotlin and Dart files need a different verification stack — `focus_owner`
gradle needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and `--rerun-tasks`; a
plain `gradlew test` reports `UP-TO-DATE` and proves nothing.

## 5. Rules that will bite you (carried forward, still true)

- **Ask before large scope changes.** The plagiarism-tools split turned into
  an archive-and-delete mid-session because the user volunteered new
  information partway through. That is fine and expected — just don't assume
  silence means "keep going as originally scoped" if something about the
  target file's relevance seems worth a quick check.
- **No suppressions, ever.** No `# noqa`, no per-file-ignore added without
  asking every time, no shellcheck disable beyond what's already justified
  inline. If you hit a rule (T201, ANN401, PLC0415, etc.) that seems to
  fundamentally conflict with the file's purpose, ask — don't suppress. Last
  session this came up for `print()` vs ruff's T201 in extracted Python
  files; the fix was converting to `sys.stdout.write()`, not a per-file-ignore.
- **A file must not assign a global it never reads** (SC2034). The hook runs
  `shellcheck` with **no `-x`**, so each file stands alone. Constants travel
  with their readers; a global genuinely written on both sides of a seam
  stays in the entry script.
- **New sourced libs need a shebang AND the executable bit.** The hook reads
  the **git index**: stage with `git add --chmod=+x`, and note that a plain
  `git add` afterwards resets it. This cost real failed pre-commit runs last
  session too — `pre-commit run --files` before `git add` does NOT catch a
  missing index executable bit; only running it against the actually-staged
  set does.
- `pre-commit run --files <changed>` before committing, but run it **after**
  `git add`, not before — index-mode checks (executable bit) only fire
  against what's staged. **`prettier` and `ci-mirror` run on pre-push.**
  `npx prettier --write` any `.md`/`.json` you touch (evidence/contract files
  included — they are JSON and prettier will reformat them).
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`. Staging **≥4 code files
  also needs** a fresh `docs/superpowers/contracts/*.json`. Put the
  **measured** coverage number in it, not a rounded-up one. Two such pairs
  already exist from last session as format references:
  `install-plagiarism-tools-split-2026-08-18.json` and
  `archive-plagiarism-tools-2026-08-18.json` (evidence + contracts).
- Work directly on `main`. `git stash` and branch creation are blocked; use
  `git worktree add --detach` for a clean baseline (but NEVER `git filter-repo`
  inside a worktree — it shares the object store with the main repo and will
  corrupt it; always a throwaway `git clone` for that, which shouldn't be
  needed this session).
- **Do not wire the file-length hook into pre-commit.** It lands last, once
  `check_file_length.sh --all` exits 0.
- Watch `jscpd` (fails above 2%). Measure in a **clean HEAD worktree** — the
  working tree reads higher because of vendored `.venv`.
- Cap pytest memory:
  `systemd-run --user --scope -p MemorySwapMax=0 -p MemoryMax=2G`.

## 6. Tooling reference

**`meta/scripts/check_file_length.sh --all`** — the 250-line gate. Run
**before every commit**.

**`meta/scripts/shell_coverage.sh <test> <subject> [min]`** — kcov wrapper,
100% minimum. Hand it the test script **directly**; `bash script.sh`
instruments the bash binary and silently reports 0/0.

**`meta/scripts/extract_shell_functions.py`** — moves functions
brace-by-brace. **Never slice by line range**: it cut through a multi-line
quoted string in a past session and left an unterminated quote that a
regex-based loader tolerated while the shell could no longer source the file.
**Do not trust where it puts the source line** — verify with `grep -c` on the
anchor and check placement; it got this wrong three times in a past session
(before a variable existed, before another variable existed so paths expanded
against an empty prefix, and on a nested re-source rather than the top-level
one).

**`meta/scripts/verify_shell_split.sh <pre-split-rev> <old> <new>...`** —
proves a split moved every function verbatim (hashes function bodies only,
blind to top-level code). For a **partial** split list the old path among the
new paths too, or it reports a false `DIFFERENCE`.

**`meta/scripts/mutate_shell.py <spec>`** — mutation testing against specs in
`meta/scripts/fixtures/mutations/`. No spec currently exists for
`libre_translate.sh` or anything outside `phone_focus_mode/`; creating one is
optional, not required by the brief — 100% line coverage with real assertions
is the stated bar, mutation testing is what `phone_focus_mode` additionally
did.

## 7. Testing pattern to follow

Last session's plagiarism-tools split established a working pattern for
`single_use/` shell scripts with no prior test coverage:

- A `lib/tests/` directory sibling to the split libs.
- A `*_harness.sh` file (sourced, not executed) with `_t_pass`/`_t_fail`/
  `_t_eq` helpers, `mktemp -d` + `trap cleanup EXIT`, and PATH-shim fakes for
  any external tool the code shells out to (record invocation to a file,
  minimum realistic behavior).
- One `test_<lib>.sh` per lib, sourcing the harness, asserting against real
  function calls (not mocks at the call-site level).
- A `test_<entry-script>.sh` that runs the **actual entry script as a
  subprocess** against the same fakes, since `verify_shell_split.sh` and kcov
  are blind to code that only lives in the entry script's `main()`.
- Two sharp edges hit and fixed last session, watch for both again:
  - `local a="$1" b="${a}"` **fails under `set -u`** — bash evaluates all
    RHS expressions in the new scope before any assignment lands, so `$a` is
    unbound when `$b`'s RHS is evaluated. Split into separate `local`
    statements.
  - A function that calls `exit` (not `return`) on a fatal condition will
    kill the whole test script if called directly inside an `if` condition —
    `exit` always terminates the process regardless of `if`/`&&` context. Run
    it in a subshell: `if (fn args); then ...`.

Check `libre_translate.sh` for anything that shells out (curl? systemctl?
some translate CLI?) before assuming the same fakes apply — it's a different
domain from the plagiarism installer, so the PATH-shim list will differ.

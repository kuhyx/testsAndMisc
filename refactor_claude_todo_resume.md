# Resume: enforce the 250-line file cap

> **Paste this whole file to a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Continues `refactor_claude_todo.md`, which is still the
> spec — read it too, but the decisions below override it where they differ.

## Where things stand

**57 files** over 250 lines (was 183 — 69% cleared). Everything is committed
to `main`; see `git log` for the head.

`focus_owner/analysis_options.yaml` is **resolved** (2026-08-16). It was not a
stray edit: `flutter pub get` writes that `analyzer.exclude` block itself
("Upgrading analysis_options.yaml to exclude build and platform directories"),
reproduced byte-identically from a clean detached worktree. It is committed, so
it will stop reappearing. Earlier handoffs called it "not ours" — that was
wrong, and the reason it kept coming back.

**`python_pkg/` is DONE — 50 violations → 0.** Do not reopen it.
**All 12 prose files are done.** `kcd2_dice_solver` is 12 → 4, all four source
files.

`git log --oneline --grep='[Ss]plit'` is the authoritative list.

## What is left

Get the real list — a per-directory table used to live here and went stale
every session:

```bash
bash ~/utils/scripts/check_file_length.sh --all
```

`linux_configuration` dominates; `phone_focus_mode` (11) is last by policy.
This handoff counts too, whenever an edit pushes it over.

### Pick targets by VERIFIABILITY, not by line count

The suggested order below sorts by cheapness. That is the wrong axis: several
"cheap" near-miss files turned out to be unverifiable, which costs more than a
big file that can be run. Triage each candidate first:

```bash
grep -cE '^\s*(cat|tee)\s*>|>\s*"?(\$HOME|\$unit_dir|/etc|/usr|/var|/opt)' <f>
grep -cE '\b(require_root|sudo -v|EUID -ne 0)\b' <f>
```

- **Both zero → take it.** Traceable, or runnable outright.
- **Writes > 0 → skip for now.** Shell redirections (`cat > /etc/...`) cannot
  be stubbed via `PATH`; running it mutates the system for real. This ruled out
  `nvidia_troubleshoot.sh` (writes `/etc/modprobe.d/`) and
  `install_usage_monitoring.sh` (writes `$HOME/.local/bin` + systemd units)
  after they had already been picked as "easy".
- **Best of all: something self-verifying.** `mtk_root/tests/run_tests.sh` was
  421 lines and the easiest split of the session, because it reports
  `58 passed, 0 failed` and the full output diffs byte-identical.

Done this session on that basis: `disk_cleanup_check.sh` (329 → 230+124),
`mtk_root/tests/run_tests.sh` (421 → 218+157+75), `meta/lint_python.sh`
(353 → 175+116+96), `EnforcementLogTest.kt` (251 → 169+90).

**Verify the branch you actually changed.** `lint_python.sh --quick` exits
before the block that was extracted, so an identical `--quick` output proved
almost nothing; the full-mode run is what mattered. Same shape as the silent-
stub trap in `docs/shell-split-verification.md`. Ask every time: did this run
enter the code I moved?

### Deliberately over the cap — a NAMED blocker, not a line-count job

Splitting one means fixing the blocker first. **Do not suppress to land one.**

| File                                    | Why                                                                                                                                                                                    |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `check_and_enable_services.sh` (1337)   | every `check_*` writes one `SERVICE_STATUS`                                                                                                                                            |
| `steam_compatibility.sh` (663)          | `CACHE_MAP` written in a lib, read by `main`                                                                                                                                           |
| `block_compulsive_opening.sh` (705)     | `install_all` copies the running script to `/usr/local/bin`; an entry+lib shape ships an entry whose `SCRIPT_DIR` has no `lib/` — breaks three daily-use apps + the pacman rewrap hook |
| `diagnose_pacman_hook_stall.sh` (493)   | `LAST_ELAPSED` / `PACMAN_BIN` cross the seam                                                                                                                                           |
| `libre_translate.sh` (488)              | ~19 globals cross any seam                                                                                                                                                             |
| `enforce_vbox_hosts.sh` (443)           | every seam falls inside a heredoc                                                                                                                                                      |
| `clean_audio.sh` (419)                  | probe-result globals through two libs                                                                                                                                                  |
| `setup_passwordless_system.sh` (374)    | no `main()`; top-level block kept by hand                                                                                                                                              |
| `install_plagiarism_tools.sh` (534)     | two heredocs emitting Python; extracting them pulls 22 ruff/pylint/mypy violations into the gate — a Python cleanup task, not a split                                                  |
| `meta/scripts/optimize_vscode.py` (498) | `_apply_variant` calls back into the caller                                                                                                                                            |

Same in TypeScript: `kcd2`'s `search.ts` and `badgeValue.ts`, and
`reverse_survivors`' `sim.ts` (`step` ⇄ `survivorStep`) and `types.ts`.

`billsplit`'s last file is Flutter's generated `win32_window.cpp`.
**Resolved 2026-08-16 — gitignore is NOT the mechanism**: it is tracked and
`billsplit/windows/runner/CMakeLists.txt:13` lists it as a build source, so a
`.gitignore` entry does nothing and `git rm --cached` breaks the Windows build
for every fresh clone. (`check.py` skips git-_ignored_ files, which is what
makes gitignore look workable — it only works for untracked ones.)

**Prerequisite of the gate-wiring step:** add a Flutter-runner exemption to
`~/utils/file_length/config.py` — a _different repo_, own gate and CI —
covering `windows/runner/`, `linux/runner/`, `macos/Runner/`, beside the
existing `GENERATED_PATTERN` rules. Land it there before wiring the hook here.

## Read these BEFORE the first split

- `docs/shell-split-recipes.md` — how to **make** a shell split.
- **`docs/shell-split-verification.md`** — how to find out it is **wrong**.
  New this session and the more important of the two. Read it first.
- `docs/app-split-recipes.md` — Dart `part`, Kotlin fixture objects, the TS
  import cycle that compiles clean, per-project test baselines.
- `docs/python-split-recipes.md` — the seam-selection rule, which generalises.

### The single most expensive lesson

**A green split can still be broken.** `analyze_repo.sh` passed `bash -n`,
`shellcheck`, two diffs and a stubbed probe, then aborted at runtime. The two
bugs (a `set -e` function tail, a self-referencing nameref), why
`verify_shell_split.sh` cannot see either, how
`meta/scripts/trace_shell_split.sh` does, and the traps in using it are all in
**`docs/shell-split-verification.md`**. Read it before any shell split; do not
re-derive it here.

Also there: why a `--skip-install` flag is not permission to run a script —
one such "safe" baseline run installed four AUR packages.

## Decisions already made (do not re-ask)

1. **Full clearance** to `--all` exit 0. When context runs out, write a fresh
   handoff like this one rather than stopping mid-way.
2. CI checks only files in the push/PR range, not `--all`.
3. `docs/superpowers/plans/**` + `sessions/**` are exempt — done.
4. `poker-stakes/` is tracked — done.
5. Prose: automate what can be automated, delete the automated lines, keep only
   HOW, never WHY.
6. Shell verification is `bash -n` + `shellcheck` + `systemctl cat` path checks.
   **Never execute an enforcement/installer script that mutates the live system
   or the phone.**
7. One commit per logical unit.
8. **Editing test files to follow moved code is allowed**, bounded by: no
   assertion changed, nothing deleted/skipped/weakened, identical pass count.
   A test harness that copies the script into a temp worktree must also copy the
   new `lib/` — that bit the `music_parallelism` split.
9. Per-commit gate is `pre-commit run --files <changed>`; the real `git commit`
   adds jscpd. Push per directory tranche.
10. **When a seam splits code covered by a per-file-ignore, fix the lint — do
    not copy the ignore onto the new file.** Ask only if the fix looks like it
    changes behaviour.
11. **The named blockers get real refactors, not exemptions** (user, 2026-08-16:
    "yes, do a real refactoring, we can take risks"). Risk is accepted on the
    blocker list — but "accepted risk" means verified against stubs, not
    unverified. Pair it with 12.
12. **Every split is verified by running, always** (user, 2026-08-16: "apply the
    full run-and-diff always"). For scripts Decision 6 forbids executing live,
    "running" means `meta/scripts/trace_shell_split.sh` — a real execution with
    mutating binaries stubbed — and a trace diff against the pre-split commit.
    Decisions 6 and 12 do not conflict; the harness is what reconciles them.
    A split verified by static checks alone is not finished.

## The constraint that will bite you

**Wire the file-length gate LAST**, only once `--all` already exits 0.
`meta/scripts/ci_mirror.sh:109` runs `pre-commit run --all-files` as a
**pre-push** hook, and `.github/workflows/pre-commit.yml:105` does the same in
CI. Registering the hook while violations remain makes **every `git push` fail**.
Do not scope around it with `exclude:`/`files:`.

Final commit, once and only once the tree is clean:

```yaml
- id: file-length
  name: file length <= 250 lines
  entry: bash /home/kuhy/utils/scripts/check_file_length.sh
  language: system
```

Plus `.github/workflows/file-length.yml` modelled on
`~/todo/.github/workflows/file-length.yml`, scoped to changed files. Then prove
it fails: stage a deliberately 251-line file, confirm `git commit` aborts,
delete it.

## Concurrency: check for another agent FIRST

A past session collided with a second Claude on the same tree and lost a
commit race to it. **Before touching the index**, run the `pgrep`/`ss` checks
in `docs/shared-checkout-safety.md`, which also covers recovering changes
stranded by a killed `pre-commit`.

## Traps that still cost time

- **`end-of-file-fixer` aborts commits.** Files built with `sed`/`cat` often
  lack a trailing newline. `git add` again and re-commit.
- **`prettier` is pre-push only.** A markdown file that passes every per-commit
  gate can still fail the push. Run `npx prettier --write <file>` on new docs.
- **`shfmt -w` deletes comment banners** it thinks are stray — it removed a
  `#====` STEP header. Re-count banners after running it. Also: 157 of 298
  `linux_configuration` shell files were **already** shfmt-dirty at the session
  start, so `run_linters` exits 1 on the full tree regardless. Do not add to it;
  do not try to fix all 157.
- **Formatters silently revert edits.** After editing, `grep` the file to
  confirm the change survived.
- **Contracts.** Staging **≥4 code files** requires a fresh
  `docs/superpowers/contracts/*.json` in the same commit, on top of the
  per-commit evidence JSON. Validate with
  `python3 meta/scripts/validate_contract.py <file>`.
- **Never edit files while a push is running** — pre-commit stashes and restores
  unstaged changes; editing in that window makes the restore fail. After any
  push confirm `git status --short --branch` does not say `ahead N`; a piped
  `git push | tail` masks failure.
- **Long commands**: background anything over ~60s.

## `phone_focus_mode` — highest blast radius, do it LAST

1. **`deploy.sh` has a hardcoded flat push list** (search `adb_cmd push`, ~lines
   374–383) with **no `lib/` subdirectory**. Every new split lib must be added
   there in the same commit, or the phone sources a missing file at runtime —
   gate green, tests green, device broken.
2. **`config.sh` (571) is sourced by 11 scripts.** Keep it as the entry point
   that re-sources its own parts, so all 11 callers keep working untouched.

Static check after each split: grep `deploy.sh`'s push list and every
`source`/`.` line in `phone_focus_mode/*.sh` and confirm each new lib appears.

## Suggested order

Run the verifiability triage above first; it outranks this list.

1. Anything self-verifying or read-only — test suites, linters, report
   scripts. Cheapest to prove, regardless of size.
2. `focus_owner` (Kotlin/Dart), `kcd2_dice_solver`, `bucket_catch`,
   `reverse_survivors` — read `docs/app-split-recipes.md` first. These have
   real test baselines (40 Kotlin, 94 Dart, 288, 160).
3. The `linux_configuration` shell scripts that write nothing.
4. The write-to-system installers, once the harness can redirect their writes
   under a temp prefix. Not tractable before that.
5. `phone_focus_mode` (11) — with the `deploy.sh` push-list guard above.
6. Gate wiring + CI workflow — last, and only after the
   `~/utils/file_length/config.py` Flutter-runner exemption lands.

**`fresh-install/main.sh` is not the easy one it looks like**: `sudo -v` and
package installs at top level, a `local -n` nameref in
`all_subpackages_installed`, and it reads `aur_packages.txt` /
`pacman_packages.txt` from the **cwd**, so a baseline must run from its own
directory or it dies at the first read and looks like a broken split.

## Done condition

```bash
cd ~/testsAndMisc && bash ~/utils/scripts/check_file_length.sh --all   # exit 0
pre-commit run --all-files                                             # passes
```

Plus: a staged 251-line file makes `git commit` fail.

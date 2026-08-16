# Resume: enforce the 250-line file cap

> **Paste this whole file to a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Continues `refactor_claude_todo.md`, which is still the
> spec — read it too, but the decisions below override it where they differ.

## Where things stand

**61 files** over 250 lines (was 183 — 67% cleared). Everything is committed
**and pushed** to `main` at `c4bdaad`. `focus_owner/analysis_options.yaml` has an
uncommitted change from an earlier session — **leave it unstaged**, it is not
ours. (It was briefly lost to a pre-commit stash this session and recovered from
`~/.cache/pre-commit/patch*`; see "If the tree looks suspiciously clean".)

**`python_pkg/` is DONE — 50 violations → 0.** Do not reopen it.
**All 12 prose files are done.** `kcd2_dice_solver` is 12 → 4, all four source
files.

`git log --oneline --grep='[Ss]plit'` is the authoritative list.

## What is left (61)

| Directory             | Count         |
| --------------------- | ------------- |
| `linux_configuration` | 32            |
| `phone_focus_mode`    | 11 (do LAST)  |
| `focus_owner`         | 5             |
| `kcd2_dice_solver`    | 4             |
| `meta`                | 3             |
| `bucket_catch`        | 2             |
| `reverse_survivors`   | 2             |
| `billsplit`           | 1 (generated) |

**Do not work from this table.** Run:

```bash
bash ~/utils/scripts/check_file_length.sh --all
```

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

`billsplit`'s last file is Flutter's generated `win32_window.cpp`; editing it
would be undone by `flutter create`, so it needs an exemption or a shrug.

## Read these BEFORE the first split

- `docs/shell-split-recipes.md` — how to **make** a shell split.
- **`docs/shell-split-verification.md`** — how to find out it is **wrong**.
  New this session and the more important of the two. Read it first.
- `docs/app-split-recipes.md` — Dart `part`, Kotlin fixture objects, the TS
  import cycle that compiles clean, per-project test baselines.
- `docs/python-split-recipes.md` — the seam-selection rule, which generalises.

### The single most expensive lesson this session

**A green split can still be broken.** `analyze_repo.sh` passed `bash -n`,
`shellcheck`, a function-set diff, a line-set diff **and** the stubbed run —
and shipped a script that aborted after language detection. Two bugs, neither
reachable by any static check:

1. **`set -e` + function tail.** `((X > 0)) && HAS_Y=true` as a _top-level_
   statement merely leaves `$?` non-zero. Wrapped into a function it becomes
   that function's **return value**, and a false one kills the script. When you
   wrap former top-level code, check the **last statement**; append `|| true`.
2. **Self-referencing nameref.** `local -n FOO="$1"` pointing at a global also
   named `FOO` still moves data on bash 5.3, but warns `circular name reference`
   on _every access_, into the script's own output. Name the local `_foo`.
   (Then shellcheck loses sight of the array → SC2034. Fix by passing the name
   through a variable, not by suppressing.)

`verify_shell_split.sh` **sources the libs and never calls them**. It proves
`source` lines resolve, nothing more. When a seam passes state, **run the
thing**: stub only what mutates the system, and diff the generated artifacts
against a detached worktree at the pre-split commit.

### `--skip-install` is not permission to run a script

`shell_check.sh` gates only `install_if_missing`'s pacman branch on
`SKIP_INSTALL`; the AUR branch in `install_linters` runs regardless. A
backgrounded "baseline" run **installed four AUR packages** before it was
killed. The user chose to leave them. Before running anything for a baseline,
grep the flag's variable and confirm it gates **every** mutation path.

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

This session collided with a **second Claude** started by
`~/.claude/scripts/claude-autoresume.sh`, running the same refactor in the same
tree. Shared git index → its files landed in my staging area and it won a commit
race. Then it **stalled for 17 minutes** and never recovered.

Its signature, if it happens again:

```bash
pgrep -af 'claude -p' | grep -v grep     # autoresume runs `claude -p ... --continue`
ps -o pid=,etime=,time= -p <pid>         # 7s CPU over 17min = not working
pgrep -P <pid> -a                        # only MCP servers = no command running
ss -tnp | grep <pid>                     # ESTAB to :443 with 0/0 queued = half-open
```

**Root cause:** a request to the API got no response, and there is no read
timeout — so it waits forever in `epoll_wait`. Its log is 0 bytes because
`claude -p` buffers all output until the run completes. `kill <pid>` is safe;
it committed its in-flight work on the way out.

**Before starting work:** run the `pgrep` above. If another agent is live in
this repo, deal with that before touching the index.

### If the tree looks suspiciously clean

Killing a process mid-`pre-commit` strands the unstaged changes it stashed.
They are recoverable — do **not** re-create them by hand:

```bash
ls -lt ~/.cache/pre-commit/patch* | head
git apply ~/.cache/pre-commit/patch<newest>
```

That is how `focus_owner/analysis_options.yaml` came back this session.

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

1. The near-miss tail (251–310) — cheapest count-per-commit. `EnforcementLogTest.kt`
   is over by **1**; `tether_enforcer.sh` by 17 (but that is `phone_focus_mode`,
   so last); `fresh-install/main.sh` (309, zero heredocs) is a clean shell one.
2. The remaining `main()`-shaped `linux_configuration` shell scripts.
3. `focus_owner` (Kotlin/Dart), `kcd2_dice_solver`, `bucket_catch`,
   `reverse_survivors` — read `docs/app-split-recipes.md` first.
4. `phone_focus_mode` (11) — with the guard above.
5. Gate wiring + CI workflow — last.

## Done condition

```bash
cd ~/testsAndMisc && bash ~/utils/scripts/check_file_length.sh --all   # exit 0
pre-commit run --all-files                                             # passes
```

Plus: a staged 251-line file makes `git commit` fail.

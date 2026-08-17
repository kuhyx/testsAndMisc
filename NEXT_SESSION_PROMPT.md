# Next session: split `install_pacman_wrapper.sh`

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The one job

Split
`linux_configuration/scripts/periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh`
(316 lines, over the 250-line cap by 66) into files that are each under the
cap, and **prove by execution** that it still does exactly the same thing.

The harness already exists and has already been run against this exact file —
its baseline is captured and its one blind spot is mapped below. Use it, don't
rebuild it.

## What landed last session (do not redo)

`install_usage_monitoring.sh` (290 lines) is done, committed and pushed as
`26965ba`: a 53-line entry plus five libs in a sibling `lib/`, with an empty
before/after trace diff including all five generated-file hashes. That split is
the worked example — read it before starting this one, the shape transfers.

Two things it discovered that this file inherits:

- The pre-commit hook runs **`shfmt -w` on every staged shell file** and
  re-stages it. It rewrites `cat > "x" << 'EOF'` to `cat >"x" <<'EOF'`. If any
  test greps a script's source text for a redirection, that rewrite silently
  breaks extraction. Run `shfmt -w` on your files yourself, then re-verify, so
  the state you tested is the state that gets committed.
- Repo-wide `jscpd` currently reports **2.51% (over the 2% gate)** from the
  working tree, but every clone above the HEAD baseline is vendored
  `.venv`/`.ci-mirror-venv` site-packages (`tqdm/completion.sh`,
  `virtualenv/activate.sh`). Measured at HEAD in a clean worktree it is 1.47%
  with 27 clones, and the committed hook run passed. Don't chase it, and don't
  "fix" it by touching vendored files.

## The baseline you must reproduce

Captured at commit `26965ba`. **Verified deterministic**: two consecutive runs
at HEAD produced byte-identical traces, so a before/after diff is real proof.

```bash
F=linux_configuration/scripts/periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh

rm -rf /tmp/pfx-before          # fresh, NOT emptied — the harness refuses a non-empty prefix
meta/scripts/trace_shell_split.sh "$F" --prefix /tmp/pfx-before \
  --bind-abs /usr/local/bin \
  --bind-abs /usr/local/share/digital_wellbeing \
  --bind-abs /usr/local/share/digital_wellbeing/virtualbox \
  --bind-abs /var/lib/pacman-wrapper \
  --out /tmp/before.txt
```

Expect **exit status 1** (see the blind spot below — this is correct, not a
failure), one stubbed call (`npm install --prefix …`), and 16 files written:

```
abs/usr/local/bin/heavy_job_lock.sh size=7221 sha=3961b14e6a6a8b86
abs/usr/local/bin/makepkg_capped size=2037 sha=3acf1189e93e5771
abs/usr/local/bin/mkpkg size=178 sha=da4a2fa3e8f5b6ab
abs/usr/local/bin/pacman_blocked_keywords.txt size=1042 sha=7bd951741c649b60
abs/usr/local/bin/pacman_greylist.txt size=174 sha=2dc47dd4a25d6aca
abs/usr/local/bin/pacman_lock_lib.sh size=6581 sha=147ea7a163000f82
abs/usr/local/bin/pacman_whitelist.txt size=6079 sha=cfec8efc4a2330c1
abs/usr/local/bin/pacman_wrapper size=29410 sha=548fc2b53ee4cea6
abs/usr/local/bin/words.txt size=1375483 sha=f5c9d52b244f9973
abs/usr/local/share/digital_wellbeing/install_leechblock.sh size=15965 sha=e4ec4b37fd9113a3
abs/usr/local/share/digital_wellbeing/leechblock_defaults.json size=51084 sha=ca068b74282921c6
abs/usr/local/share/digital_wellbeing/package.json size=258 sha=618fa688d2edfa4f
abs/usr/local/share/digital_wellbeing/seed_leechblock_storage.js size=4176 sha=1611cb17124fd388
abs/usr/local/share/digital_wellbeing/virtualbox/enforce_vbox_hosts.sh size=12601 sha=ab039aedc3cd84cd
abs/var/lib/pacman-wrapper/policy.sha256 size=412 sha=0aa8d95524660324
abs/var/lib/pacman-wrapper/source.sha256 size=1374 sha=4c928a499d437070
```

The last stderr line is
`ln: failed to create symbolic link '/usr/bin/pacman': Permission denied`.

Capture the baseline at HEAD **before editing anything**, then diff your split
against it. Unlike last file, a detached worktree is fine here — nothing
interpolates the repo path into a generated artifact (verified: the drift
manifest hashes source files by `readlink -f`, and those hashes are of file
_contents_, not paths).

## The one blind spot — this is the whole design constraint

`--bind-abs /usr/bin` **cannot be used**: it mounts an empty overlay over the
directory the sandbox needs to exec anything, and the run dies with
`bwrap: execvp bash: No such file or directory` before reaching the script.
Measured last session; it is a hard limit of the harness.

So the trace reaches **line 304** (`ln -sf "$WRAPPER_DEST" /usr/bin/pacman`),
hits EPERM, and exits 1. Lines 304 and 306 (the final `echo`) are the only
statements that never execute — everything before them is covered, 16 files
written and 19 stdout lines deep.

**Therefore: keep lines 304–316 in the entry script.** Anything you move into a
lib gets proven by the trace; anything at or after 304 does not, and a broken
split there would diff clean. This is a constraint on where the seams go, not a
reason to skip the file.

Note the absolute-path scanner does **not** list `/usr/bin` when it refuses to
run — it follows variables into `cat >`/`cp` and misses the literal `ln -sf`
target. Don't read its list as complete.

## Hazards specific to THIS file

### 1. It self-sudos at line 9

```bash
if [ "$EUID" -ne 0 ]; then
	sudo "$0" "$@"
	exit $?
fi
```

Under `--bind-abs` the run is already uid 0 (bwrap `--unshare-user --uid 0`),
so this branch is skipped and the script proceeds for real — that is why the
trace is 16 files deep rather than the three-line `require_root` truncation.
If you move this block, `$0` must still be the entry point.

### 2. `source.sha256` is a drift manifest — but a split does not disturb it

Line ~247 hashes seven **source** files (`WRAPPER_SOURCE`, `LOCK_LIB_SOURCE`,
`BLOCKED_SOURCE`, `GREYLIST_SOURCE`, `MAKEPKG_CAPPED_SOURCE`, `MKPKG_SOURCE`,
`WHITELIST_SOURCE`) plus the installed lock lib. Checked: it does **not** hash
the installer itself, and there is no glob that would pick up a new `lib/`.
So `sha=4c928a499d437070` should stay put across a split — if it moves, you
changed one of those seven copied files, which is a real regression.

`check_and_enable_services.sh` replays this manifest with `sha256sum -c` from
systemd with `cwd=/`, which is why the entries must be absolute
(`readlink -f`). Don't make those paths relative while tidying.

### 3. `chattr +i` / immutability

The script makes policy files immutable and has unlock/relock helpers
(`is_immutable_file`, `unlock_immutable_file_if_needed`,
`relock_files_on_exit`, lines 58–84) wired to a trap. Inside the sandbox these
warn ("Could not make integrity file immutable") and continue — that warning is
in the baseline and is expected. If you move the trap or the helpers, check the
trap still fires from the entry script.

### 4. It writes a _live_ system when run for real

`/usr/bin/pacman` is currently a symlink to `/usr/local/bin/pacman_wrapper`.
The sandbox protects this (the `ln` is denied — that denial is the positive
proof the bind worked), but **never run this script outside the harness** to
"check something".

## Rules that will bite you

- **`SCRIPT_DIR` must resolve symlinks**:
  `SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"`. The
  `SOURCE_*` vars are built from `dirname "$0"` and the code comments say so
  explicitly — if you move that computation into a lib, pass the value in
  rather than recomputing it at a different directory depth.
- **Wrapping top-level code in a function changes what `set -e` sees.** A bare
  `((x > 0)) && FLAG=true` as a function's last statement becomes its return
  value; if false, the script dies. Check the last statement of every function
  you create; append `|| true` if it is a bare conditional.
- **No suppressions.** No `# shellcheck disable`, no per-file ignores.
- New `.sh` files need the executable bit, a `#!/bin/bash` shebang, and **no
  `set -euo pipefail`** (a sourced lib inherits the caller's strict mode).
  Convention: a sibling `lib/` directory; see the `bin/lib/` that landed in
  `26965ba`.
- Every commit touching code needs an evidence JSON in
  `docs/superpowers/evidence/`; **≥4 staged code files** additionally needs a
  fresh `docs/superpowers/contracts/*.json`. Validate both with
  `python3 meta/scripts/validate_contract.py` /
  `meta/scripts/validate_evidence.py` before committing.
- Markdown needs `npx prettier --write` — prettier is pre-push only, so a file
  that passes every per-commit gate can still fail the push.
- Work directly on `main`; commit and push. `git stash` and branch creation are
  blocked by hooks.
- `git push` runs `ci-mirror` (clean-venv install + `pre-commit --all-files` +
  pytest) and takes minutes. Never edit files while a push is running.
- **Do not wire the file-length pre-commit hook.** It must land last, only once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0, or every push
  fails.

## Read these first

1. `docs/shell-split-verification.md` — how a green split is still broken. The
   `--prefix` section covers the manifest, the empty-prefix rule, the
   `require_root` truncation trap, and the `/usr/bin` limit above.
2. `docs/shell-split-recipes.md` — how to actually make a split.
3. The `26965ba` diff — the worked example of the entry+lib shape.

## Definition of done

- `install_pacman_wrapper.sh` and every file split out of it are **under 250
  lines** (`bash ~/utils/scripts/check_file_length.sh --all` no longer lists
  any of them).
- `diff /tmp/before.txt /tmp/after.txt` is **empty** — same exit status (1),
  same stubbed call, and all 16 content hashes identical.
- Nothing you moved into a lib sits at or after line 304.
- `shellcheck` clean and `shfmt` clean on every touched file; zero
  suppressions.
- `/usr/bin/pacman` still symlinks to `/usr/local/bin/pacman_wrapper` and
  `pacman --version` still works, after every verification run.
- Committed and pushed, with evidence (and a contract if ≥4 code files).

## If there is time

Take the next target by the same method. Pick by **verifiability**, not by line
count — a big file you can run beats a small one you cannot:

```bash
bash ~/utils/scripts/check_file_length.sh --all
```

Remaining newly-unblocked targets, ascending difficulty: `nvidia_troubleshoot.sh`
(336, needs `--bind-abs /etc/modprobe.d --bind-abs /etc/X11 --bind-abs
/etc/profile`; it embeds `$(date)` in its config so that one hash varies every
run — compare file list and sizes instead), `setup_thorium_startup.sh` (443),
`install_leechblock.sh` (485 — confirm where `INSTALL_ROOT`/`VERSION_DIR` point
BEFORE the first run, it uses `rsync -a --delete`).

**Still out of scope:** `block_compulsive_opening.sh` (705) — `install_all`
copies the running script into `/usr/local/bin`, and an entry+lib shape ships
an entry whose `SCRIPT_DIR` has no `lib/`, breaking three daily-use apps plus
the pacman rewrap hook. Leave it.

Also still blocked on a NAMED blocker, not on line count — do not "just split"
these: `check_and_enable_services.sh` (1337, every `check_*` writes one
`SERVICE_STATUS`), `steam_compatibility.sh` (663), `libre_translate.sh` (488,
~19 globals cross any seam), `enforce_vbox_hosts.sh` (443, every seam falls
inside a heredoc). See `refactor_claude_todo_resume.md`.

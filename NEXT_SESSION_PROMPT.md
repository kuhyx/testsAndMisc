# Next session: split `install_leechblock.sh`

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The one job

Split
`linux_configuration/scripts/periodic_background/digital_wellbeing/install_leechblock.sh`
(485 lines, over the 250-line cap by 235) into files that are each under the
cap, and **prove by execution** that it still does exactly the same thing.

This is the best-conditioned target left: it is the only remaining one that
traces **to completion with exit 0**, and its 93 written-file hashes are
identical across runs. Read the safety note below before you run it, though —
it kills browsers.

## What landed in the last session (do not redo)

Two splits, both committed and pushed, both proven by an empty before/after
trace diff:

- `install_usage_monitoring.sh` 290 → 53-line entry + 5 libs (`26965ba`)
- `install_pacman_wrapper.sh` 316 → 128-line entry + 4 libs (`4eedc17`)

Read the `4eedc17` diff first — it is the closest worked example, and three of
its lessons apply directly here:

- **Keep path/variable definitions in the ENTRY script, not a `lib/paths.sh`.**
  A definitions-only lib assigns without referencing, which is SC2034 on every
  variable, and suppressions are forbidden. Libs that only _reference_ globals
  are fine. `export` silences it but leaks the variables into every child
  process — a behaviour change the trace cannot see. Don't.
- **The pre-commit hook runs `shfmt -w` on staged shell files** and re-stages
  them, rewriting `cat > "x" << 'EOF'` into `cat >"x" <<'EOF'`. Run `shfmt -w`
  yourself first, then verify, so the tested state is the committed state.
- **Enumerate every test that greps the target's source text before designing
  the seams.** The pacman split had eight such assertions across two test libs;
  one (`chattr +i`) was missed on the first pass and failed loudly. Run:
  ```bash
  grep -rn 'install_leechblock' linux_configuration/tests/ meta/ .github/
  ```

Repo-wide `jscpd` reports 2.51% from the working tree but 1.47% at HEAD in a
clean worktree — the excess is entirely vendored `.venv`/`.ci-mirror-venv`
site-packages. Don't chase it; measure in a worktree if you need a real number.

## SAFETY: this script kills browsers and deletes directories

Two hazards, both measured:

1. **Line ~217 runs
   `pkill -f 'google-chrome|chromium|brave-browser|vivaldi|thorium'`.** `pkill`
   is NOT in the harness stub set, and `--prefix` cannot contain it — signals
   are not filesystem writes. Tracing this script closes every open browser.
   Check nothing is running (`pgrep -af 'chrome|chromium|thorium'`) and pass
   `--stub pkill` before any run.
2. **It runs `rsync -a --delete` at `$XDG_DATA_HOME/leechblockng`.** This is
   safe under `--prefix` — the harness exports `XDG_DATA_HOME` into the prefix
   explicitly _because of this script_ — but never run it outside the harness.

Verified after the probe runs: `~/.local/share/leechblockng/` untouched (still
dated Aug 9), no Chrome profile file modified, `/usr/local/bin/browser-preexec-wrapper`
untouched. The node seeder resolves profiles via `os.homedir()`, which the
prefix redirects, so it found no profiles and wrote nothing ("Seeding" appears
zero times in the trace).

## The baseline

```bash
F=linux_configuration/scripts/periodic_background/digital_wellbeing/install_leechblock.sh

rm -rf /tmp/pfx-before        # fresh, NOT emptied — the harness refuses a non-empty prefix
meta/scripts/trace_shell_split.sh "$F" --prefix /tmp/pfx-before \
  --stub pkill --out /tmp/before.txt
```

Expect **exit 0** and **93 files written**. Note the probe baseline was
captured _without_ `--stub pkill`; adding the stub is correct and may add one
line to the stubbed-call list, so capture your own baseline with the same flags
you will use afterwards.

**Two things vary between runs and are NOT split defects** — normalize them
before diffing:

- The prefix path is echoed inside the six `sudo sed -i …--load-extension=…`
  stubbed calls.
- `curl`'s progress meter (download speeds/times) in stderr.

Everything else is stable: all 93 content hashes were byte-identical across two
consecutive HEAD runs. The manifest section alone is the real assertion:

```bash
sed -n '/=== files written/,/=== stdout/p' /tmp/before.txt > /tmp/before.man
sed -n '/=== files written/,/=== stdout/p' /tmp/after.txt  > /tmp/after.man
diff /tmp/before.man /tmp/after.man     # must be empty
```

Also diff the full traces with the two varying patterns normalized, so a change
in stdout ordering or a dropped step still shows.

## Hazards specific to THIS file

### 1. `SCRIPT_DIR` at line ~205 finds sibling data files

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULTS_SRC="$SCRIPT_DIR/leechblock_defaults.json"
```

It also locates `seed_leechblock_storage.js` and `node_modules/`. In a sourced
lib `${BASH_SOURCE[0]}` resolves to `lib/`, so these would silently point at
`lib/leechblock_defaults.json` and the defaults would be skipped with only a
warning — exit status unchanged. Compute it once in the entry and let libs read
it, exactly as `REPO_DIR` was handled in `26965ba`.

### 2. Network downloads make timing non-deterministic

`curl` fetches the LeechBlockNG tarball and jQuery UI. Content is stable (same
hashes across runs) but progress output is not. Do not `--stub curl` — that
would skip the download and empty out most of the 93 files.

### 3. A `trap 'rm -rf "$tmpdir"' EXIT` is set mid-script

Set inside the download branch (~line 143). If you move that branch into a lib,
the trap still registers globally, but check it is not overwritten by another
`trap … EXIT` you introduce.

## Rules that will bite you

- **`SCRIPT_DIR` must resolve symlinks** in the entry:
  `SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"`.
- **Wrapping top-level code in a function changes what `set -e` sees.** A bare
  `[[ -n $x ]] && arr+=("$x")` as a function's last statement becomes its
  return value; append `|| true` if so.
- **No suppressions.** No `# shellcheck disable`, no per-file ignores.
- New `.sh` libs need the executable bit, a `#!/bin/bash` shebang, and **no
  `set -euo pipefail`** (a sourced lib inherits the caller's strict mode).
- **Verify with `pre-commit run shellcheck --files …`, not a bare
  `shellcheck -x`.** The latter follows `source=` directives and hides SC2034
  in a standalone lib; the former is the real gate and does not.
- Every commit touching code needs an evidence JSON in
  `docs/superpowers/evidence/`; **≥4 staged code files** additionally needs a
  fresh `docs/superpowers/contracts/*.json`. Validate both with
  `python3 meta/scripts/validate_contract.py` /
  `meta/scripts/validate_evidence.py`.
- Markdown needs `npx prettier --write` — prettier is pre-push only.
- Work directly on `main`; commit and push. `git stash` and branch creation are
  blocked by hooks.
- `git push` runs `ci-mirror` and takes minutes. Never edit files while a push
  is running.
- **Do not wire the file-length pre-commit hook.** It must land last, only once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0.

## Read these first

1. `docs/shell-split-verification.md` — how a green split is still broken. Now
   covers the `/usr/bin` bind limit, the unstubbed `pkill`, and how to compare
   when the target embeds a timestamp.
2. `docs/shell-split-recipes.md` — how to actually make a split.
3. The `4eedc17` and `26965ba` diffs — two worked examples of the entry+lib
   shape.

## Definition of done

- `install_leechblock.sh` and every file split out of it are **under 250
  lines**.
- The trace manifest (93 files, all hashes) is identical before and after, and
  the normalized full traces are identical, both at exit 0.
- Any test that greps the installer's source text still passes, with no
  assertion weakened.
- `pre-commit run shellcheck` clean, `shfmt` clean, zero suppressions.
- `~/.local/share/leechblockng/` and all Chrome profile dirs unmodified by the
  verification runs — check mtimes before and after.
- Committed and pushed, with evidence (and a contract if ≥4 code files).

## Ruled out — do not attempt these

- **`nvidia_troubleshoot.sh` (336).** Measured this session: its trace dies at
  step 3 because `backup_file` writes `/etc/profile.backup.<stamp>`, a _new
  sibling_ in unbound `/etc` (a file bind cannot cover siblings, and bare
  `/etc` is refused). 239 of its 336 lines never execute. Keeping the unproven
  ones in the entry — the rule the pacman split established — leaves the entry
  at ~265, still over the cap. It cannot satisfy both the rule and the goal.
- **`block_compulsive_opening.sh` (705)** — `install_all` copies the running
  script into `/usr/local/bin`; an entry+lib shape ships an entry whose
  `SCRIPT_DIR` has no `lib/`, breaking three daily-use apps plus the pacman
  rewrap hook.
- Blocked on NAMED blockers, not line count:
  `check_and_enable_services.sh` (1337), `steam_compatibility.sh` (663),
  `libre_translate.sh` (488), `enforce_vbox_hosts.sh` (443). See
  `refactor_claude_todo_resume.md`.

`setup_thorium_startup.sh` (443) is unprobed — trace it at HEAD before
committing to it, the same way this one was probed.

## Known pre-existing failure (not yours)

`bash linux_configuration/tests/test_security_hardening.sh` exits 1 at HEAD
with exactly one failure, `❌ FAIL: Compulsive block wrappers installed`. It
belongs to `block_compulsive_opening.sh`. Capture it before and after your
change and confirm it is unchanged; do not try to fix it.

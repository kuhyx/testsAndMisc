# Next session: `install_leechblock.sh` is BLOCKED — read this first

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## Do not split `install_leechblock.sh`

The previous brief pointed here. It was wrong, and the reason is worth reading
before picking any target.

`install_leechblock.sh` traces beautifully — exit 0, 93 written files, all 93
hashes byte-identical across runs with `--stub pkill`. By every signal the
harness gives you, it is the best-conditioned target left. **It is still
unsplittable in an entry+`lib/` shape**, because it is DEPLOYED as a single
file:

- `install_pacman_wrapper.sh` `cp`s it to
  `/usr/local/share/digital_wellbeing/install_leechblock.sh` (confirmed
  present on this machine, byte-identical to the repo copy, no `lib/`).
- `pacman_wrapper.sh:831` _prefers that deployed copy_, and
  `auto_install_leechblock "$@"` runs on **every pacman invocation**.
- `check_and_enable_services.sh:46` also references it, and
  `periodic-system-maintenance.timer` is active (hourly).

An entry whose `SCRIPT_DIR` has no `lib/` dies on its first `source` under
`set -e`. **The trace cannot see this** — it runs the repo copy, where `lib/`
exists. This is the same blocker as `block_compulsive_opening.sh`.

Splitting it is possible but is a _two-file_ job: teach the pacman installer to
deploy `lib/` too, which changes that file's 16-entry trace manifest and forces
a re-baseline of a file that was verified last session. Decide that deliberately
if you take it on; don't stumble into it.

**Generalise the lesson:** before designing seams, run

```bash
grep -rn '<target-basename>' linux_configuration/ --include='*.sh' \
  | grep -v '<the target itself>:'
```

A target invoked as `$CONFIG_DIR/scripts/...` (from the repo) is safe; one that
is `cp`'d somewhere and run from there is not.

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

## The job: pick a target, then prove it

There is no pre-chosen target this session (see "Ruled out" below for why).
The method is what carries over, and it is not negotiable: **prove the split by
executing the script before and after, and diffing the traces.**

```bash
# 1. Does anything deploy this file elsewhere? If yes, STOP (see above).
grep -rn '<basename>' linux_configuration/ --include='*.sh' | grep -v '<target>:'

# 2. Baseline at HEAD, BEFORE editing. Fresh, non-existent prefix.
meta/scripts/trace_shell_split.sh <target> --prefix /tmp/pfx-before \
  --stub pkill --out /tmp/before.txt

# 3. Run it twice at HEAD and diff, to learn what varies legitimately
#    (timestamps, curl progress, the echoed prefix path) before you trust it.

# 4. Split. Then re-trace into a DIFFERENT fresh prefix and diff.
```

**Coverage decides the seams.** Whatever the trace does not execute stays in
the entry script, because a split that relocates unexecuted code cannot be
verified by the diff. Read the trace's stdout against the target's guarded
blocks and enumerate what was skipped before choosing where to cut.

## Rules that will bite you

- **Keep variable ASSIGNMENTS in the entry; move FUNCTION DEFINITIONS freely.**
  A lib that assigns without referencing is SC2034 on every variable, and
  suppressions are forbidden. A lib that only references globals is clean.
  `export` silences SC2034 while leaking the variables into every child
  process — a behaviour change the trace cannot see. Don't.
- **Verify with `pre-commit run shellcheck --files …`, not a bare
  `shellcheck -x`.** The latter follows `source=` directives and hid 36 SC2034
  findings in a standalone lib; the former is the real gate.
- **The pre-commit hook runs `shfmt -w` on staged shell files** and re-stages
  them, rewriting `cat > "x" << 'EOF'` into `cat >"x" <<'EOF'`. Run `shfmt -w`
  yourself first, then verify, so the tested state is the committed state.
- **Enumerate every test that greps the target's source text before cutting.**
  The pacman split had eight such assertions across two test libs; one
  (`chattr +i`) was missed on the first pass and failed loudly.
- **Wrapping top-level code in a function changes what `set -e` sees.** A bare
  `[[ -n $x ]] && arr+=("$x")` as a function's last statement becomes its
  return value; append `|| true` if so.
- New `.sh` libs need the executable bit, a `#!/bin/bash` shebang, and **no
  `set -euo pipefail`** (a sourced lib inherits the caller's strict mode).
- Every commit touching code needs an evidence JSON in
  `docs/superpowers/evidence/`; **≥4 staged code files** additionally needs a
  fresh `docs/superpowers/contracts/*.json`. Validate both with
  `python3 meta/scripts/validate_contract.py` /
  `meta/scripts/validate_evidence.py`.
- Markdown needs `npx prettier --write` — prettier is pre-push only.
- Work directly on `main`; commit and push. `git stash` and branch creation are
  blocked by hooks. `git push` runs `ci-mirror` and takes minutes — never edit
  files while a push is running.
- **Do not wire the file-length pre-commit hook.** It must land last, only once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0. 55 files are still
  over.

Repo-wide `jscpd` reports 2.51% from the working tree but 1.47% at HEAD in a
clean worktree — the excess is entirely vendored `.venv`/`.ci-mirror-venv`
site-packages. Don't chase it; measure in a worktree if you need a real number.

## Read these first

1. `docs/shell-split-verification.md` — how a green split is still broken. Now
   also covers the deployed-copy blocker, the `/usr/bin` bind limit, the
   unstubbed `pkill`, processes the prefix cannot contain, and how to compare
   when the target embeds a timestamp.
2. `docs/shell-split-recipes.md` — how to actually make a split.
3. The `4eedc17` and `26965ba` diffs — two worked examples of the entry+lib
   shape.

## Definition of done

- The target and every file split out of it are **under 250 lines**.
- The before/after traces are identical once known-variable patterns are
  normalized, with every written-file hash unchanged.
- Nothing moved into a lib sits in a region the trace never executed.
- Any test that greps the target's source text still passes, with no assertion
  weakened.
- `pre-commit run shellcheck` clean, `shfmt` clean, zero suppressions.
- The live system is untouched by the verification runs — check mtimes of
  whatever the script writes, before and after.
- Committed and pushed, with evidence (and a contract if ≥4 code files).

## Ruled out — do not attempt these

- **`install_leechblock.sh` (485)** — see the top of this file. Traces
  perfectly, but is deployed as a single file and run from
  `/usr/local/share/digital_wellbeing/` on every pacman invocation.
- **`setup_thorium_startup.sh` (443)** — traces to exit 0 with all 8 steps
  covered and has no deployed copy, so it _is_ mechanically splittable. Do not
  split it anyway: **the thing it configures is dead.** Thorium was removed from
  this machine (chromium/librewolf are used now), `/usr/local/bin/thorium-browser`
  is a leftover symlink to `browser-preexec-wrapper`, and the enabled
  `thorium-fitatu-startup.service` fails silently at every boot:
  `thorium-browser: line 33: /https://www.fitatu.com/app/planner: No such file
or directory` — while systemd still reports `status=0/SUCCESS`. Splitting a
  443-line script to keep a broken autostart under a line cap is the wrong
  work. Either retarget it at chromium/librewolf or delete it and the unit;
  ask the user which. That decision is worth more than the split.
- **`nvidia_troubleshoot.sh` (336).** Its trace dies at step 3 because
  `backup_file` writes `/etc/profile.backup.<stamp>`, a _new sibling_ in
  unbound `/etc` (a file bind cannot cover siblings, and bare `/etc` is
  refused). 239 of its 336 lines never execute. Keeping the unproven ones in
  the entry — the rule the pacman split established — leaves the entry at
  ~265, still over the cap.
- **`block_compulsive_opening.sh` (705)** — `install_all` copies the running
  script into `/usr/local/bin`; same deployed-copy blocker as leechblock.
- Blocked on NAMED blockers, not line count:
  `check_and_enable_services.sh` (1337), `steam_compatibility.sh` (663),
  `libre_translate.sh` (488), `enforce_vbox_hosts.sh` (443). See
  `refactor_claude_todo_resume.md`.

**There is no easy next target.** Every remaining file under ~500 lines is now
either blocked by a deployed copy, unverifiable by trace, or configures
something dead. Pick by re-probing, not by line count, and expect the next win
to cost more than the last two.

`docs/shell-split-verification.md` is itself 272 lines, over the cap. Split it
when someone is doing docs work; it is not urgent and the hook is not wired.

## Known pre-existing failure (not yours)

`bash linux_configuration/tests/test_security_hardening.sh` exits 1 at HEAD
with exactly one failure, `❌ FAIL: Compulsive block wrappers installed`. It
belongs to `block_compulsive_opening.sh`. Capture it before and after your
change and confirm it is unchanged; do not try to fix it.

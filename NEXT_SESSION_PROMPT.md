# Next session: make write-to-system installers traceable

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The one job

Extend `meta/scripts/trace_shell_split.sh` so that scripts whose job is
**placing files** can be executed safely and diffed. Right now they are the
only class of remaining file-length violations that cannot be verified at all,
which blocks roughly half of what is left.

This is a **tooling task, not a split.** Do not split any script this session
until the harness change is landed and proven. Then, if there is room, use it.

## Why this is blocking

`meta/scripts/trace_shell_split.sh` (read it first, ~180 lines) runs a script
with mutating _binaries_ shadowed by `PATH` stubs that record their calls and
exit 0. That works for `sudo`, `pacman`, `systemctl`, `adb`, `mount`, and about
25 more.

It does **not** work for shell redirections. `cat > /etc/modprobe.d/x.conf` and
`cat > "$HOME/.local/bin/foo.sh"` are bash builtins-plus-redirection; no `PATH`
entry can intercept them. So today the choice for these scripts is: stub the
copy tools and get a nearly empty trace, or run for real and rewrite the live
system. Both are useless.

Concrete blocked files (all real, all currently unverifiable):

| File                                | Writes                                                                                 |
| ----------------------------------- | -------------------------------------------------------------------------------------- |
| `nvidia_troubleshoot.sh` (336)      | `cat > /etc/modprobe.d/nvidia-gsp-disable.conf`, `mkinitcpio`                          |
| `install_usage_monitoring.sh` (290) | `$HOME/.local/bin/*.sh`, `$unit_dir/*.service`, `*.timer`                              |
| `install_pacman_wrapper.sh` (316)   | the pacman wrapper + immutable-file handling                                           |
| `block_compulsive_opening.sh` (705) | copies the running script into `/usr/local/bin`                                        |
| `install_leechblock.sh` (485)       | `mkdir -p`/`rsync`/`cp -a` into `$INSTALL_ROOT`, `$VERSION_DIR`                        |
| `setup_thorium_startup.sh` (443)    | `cat >` a launcher + a `.service`; `sudo -u` `mkdir -p` into systemd/autostart/i3 dirs |

`block_compulsive_opening.sh` is the highest-stakes one: the handoff records
that a bad split there "breaks three daily-use apps + the pacman rewrap hook".
Treat it as the last of this group, not the first.

## What is already known about the shape

Run these before designing anything — the answers are load-bearing:

```bash
grep -n 'unit_dir=' linux_configuration/scripts/periodic_background/system-maintenance/bin/install_usage_monitoring.sh
grep -rhoE '>\s*"?(/etc|/usr/local/bin|/usr/share|/var/lib|\$HOME[^"]*)' <each file above>
```

Measured on 2026-08-16: most destinations are **`$HOME`-rooted variables**
(`unit_dir="$HOME/.config/systemd/user"`), not hardcoded absolutes. That
matters, because redirecting `HOME` to a temp dir handles a large share with
**no change to the scripts themselves**. The genuinely hardcoded `/etc` and
`/usr/local/bin` writes are the smaller, harder residue — decide explicitly how
to treat those rather than assuming one mechanism covers everything.

Two cases that a bare `HOME` redirect will **not** catch, so design against
them rather than discovering them later:

- `setup_thorium_startup.sh` writes via `sudo -u "$SUDO_USER" mkdir -p ...`.
  `sudo` is already stubbed to exit 0 without running its argument, so those
  directories are never created and anything depending on them takes a
  different path. Decide whether the `sudo` stub should _execute_ its argument
  under the prefix instead of swallowing it — that is a real behaviour change
  to the harness and affects every existing trace.
- `install_leechblock.sh` writes through `rsync -a --delete` and `cp -a` into
  `$INSTALL_ROOT` / `$VERSION_DIR`. `--delete` against a wrong root is
  destructive, so confirm where those variables point _before_ the first run.

## Design constraints (do not violate)

1. **Never mutate the real system to verify a split.** This is Decision 6 in
   `refactor_claude_todo_resume.md` and it is not negotiable. The whole point of
   the harness is that it makes running these scripts safe.
2. **The trace must still be diffable** — same format as today: exit status,
   ordered stubbed calls with arguments, stdout, stderr. A before/after diff at
   a detached worktree is how a split gets proved.
3. **A silent stub is a trap, not a pass.** `--stub du` with no value makes
   every `((size > 0))` false and the trace walks past every guarded branch;
   two such traces match while exercising nothing. Any redirect you add must
   not create the same illusion — if a write is redirected, the trace should
   _show_ the write, with its destination and ideally its content hash.
4. **Do not weaken the gate to land this.** No suppressions, no `exclude:`.
5. `trace_shell_split.sh` is itself under the 250-line cap. If the change
   pushes it over, split it — the harness is not exempt from the rule it serves.

## Suggested approach (your call — argue if you disagree)

A `--prefix <dir>` flag that runs the target with `HOME` pointed at a temp tree
and, for the hardcoded-absolute residue, either a `bwrap`/`fakeroot` bind-mount
of `/etc` and `/usr/local` or an explicit refusal with a clear message. Prefer
one honest mechanism plus a named limitation over two half-working ones.

Whatever you choose, the acceptance test is the same: pick
`install_usage_monitoring.sh`, trace it, and confirm the trace shows the unit
files being written **into the prefix**, with `~/.config/systemd/user/` and
`~/.local/bin/` on the real machine untouched afterwards (`ls -la` them, and
check `systemctl --user list-unit-files | grep usage-report` is unchanged).

## Verify it the way this repo verifies things

- Prove the harness catches a **real** break, not just that it runs. The
  existing fixtures in the session log did this by reproducing the two
  documented bug classes; do the equivalent for redirected writes — e.g. a
  fixture whose split drops a write, and confirm the trace diff shows it.
- Re-run the three existing regression fixtures (the `set -e` function-tail
  abort, the self-referencing nameref, the valued-stub branch test) so the
  change does not weaken what already works.
- `shellcheck` + `shfmt -d` clean, **fixing** findings rather than suppressing.
- `pre-commit run --files <changed>` before committing; the real `git commit`
  additionally runs jscpd.

## Repo rules that will bite you

- Every commit touching code needs an evidence JSON in
  `docs/superpowers/evidence/`; **≥4 staged code files** additionally needs a
  fresh `docs/superpowers/contracts/*.json`
  (`python3 meta/scripts/validate_contract.py <file>`).
- New `.sh` files need the executable bit or the commit hook rejects them.
- Markdown needs `npx prettier --write` — prettier is pre-push only, so a file
  that passes every per-commit gate can still fail the push.
- Work directly on `main`; commit and push. `git stash` and branch creation are
  blocked by hooks. Use `git worktree add --detach` for a clean baseline.
- `git push` runs `ci-mirror` (clean-venv install + `pre-commit --all-files` +
  pytest) and takes minutes. Never edit files while a push is running.
- **Do not wire the file-length pre-commit hook.** It must land last, only once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0, or every push
  fails. See "The constraint that will bite you" in the handoff.

## Read these first

1. `meta/scripts/trace_shell_split.sh` — the thing you are changing.
2. `docs/shell-split-verification.md` — how a green split is still broken;
   includes the silent-stub trap, the symlink-entry-point trap, and the
   existing limits of the harness.
3. `refactor_claude_todo_resume.md` — current state (57 files over the cap),
   the decisions already made, and the verifiability triage for picking targets.

## Definition of done

- `trace_shell_split.sh` can execute at least `install_usage_monitoring.sh` and
  `nvidia_troubleshoot.sh` and produce a diffable trace.
- The real `~/.config/systemd/user/`, `~/.local/bin/` and `/etc/modprobe.d/` are
  provably untouched after those runs.
- The three existing regression fixtures still behave.
- A fixture proves the trace diff **detects** a dropped write.
- Committed and pushed, with evidence (and a contract if ≥4 code files).

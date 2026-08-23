# testsAndMisc restructure — DONE

**The campaign is finished. There is no next step in it.**

The directory-depth cap enforces, both remaining units are their own repos,
and every stale live reference is gone. What follows is the closing state and
the handful of things deliberately left undone.

Superseded: `NEXT_SESSION_PROMPT.md` and `NEXT_SESSION_RESTRUCTURE.md` (merged
here 2026-08-23). `INSTALLER_FIX_TASK.md` is a **different, still-open** job.

## Closing state (2026-08-23, all pushed, `main` clean)

```
depth violations     0   (was 46; the gate now runs WITHOUT --warn)
source files       949 / 1200 ceiling
tracked files     1090   (2295 at the campaign start)
stale live refs      0   (was 8, pre-existing from the flatten)
```

Verify any of it:

```bash
./meta/scripts/check_directory_depth.sh --all     # exits 0
./meta/scripts/check_repo_size.sh
./meta/scripts/report_live_state.sh --check
```

## What landed this session

**`hosts-blocker`** — [github.com/kuhyx/hosts-blocker](https://github.com/kuhyx/hosts-blocker),
cloned at `~/hosts-blocker`. 52 commits.

**`digital-wellbeing`** — [github.com/kuhyx/digital-wellbeing](https://github.com/kuhyx/digital-wellbeing),
cloned at `~/digital-wellbeing`. 89 commits, and it carries the six suites that
used to sit in `linux_configuration/tests/`.

**The cap enforces.** `--warn` is gone from the `directory-depth-cap` hook, and
its name changed from "Report paths over" to "Enforce". Re-adding `--warn`
re-opens the hole; put the offending path somewhere legal instead.

**Live repairs.** Five mechanisms were silently pointing at deleted paths and
none of them said so:

- `hosts-file-monitor.service` (active) had logged **37** failures to restore
  `/etc/hosts` — it detected tampering it could not repair.
- `dns-blocklist-refresh.service` (enabled, runs 00:01) and
  `media-organizer.service` named pre-flatten `single_use/` paths.
- `setup_periodic_system.sh` read **all ten** of its templates from a
  directory holding only untracked build residue since `system-maintenance`
  was extracted.
- The pacman-wrapper drift manifest embeds **absolute** paths, so
  `check_and_enable_services.sh` reported a permanent false "stale or
  tampered". It now verifies.

Backups of every live artifact: `/var/tmp/*.pre-{extract,fix,dw}`.

**Deleted.** `.hippo/` (161 files, 0 retrievals ever) and 3.7 GB of untracked
extraction residue. Before deleting the latter, `focus_owner/android/key.properties`
was preserved to `~/.android/release/key.properties` (mode 600) — it holds the
**Android release signing password**, it is correctly gitignored, and those two
copies were the only ones on the machine.

## Deliberately NOT done

- **Nextcloud dedup** — measured and recommended against. 3,618 lines across
  22 files; the `nc_*` and `rpi_nc_*` families are parallel _evolutions_, not
  copies; only 3 of 15 libs have tests; the target is a Raspberry Pi that
  cannot be reached from here. Do not attempt without hardware access.
- **The unwrapped `discord` / `signal-desktop` binaries.** `test_security_hardening.sh`
  reports 18 passed / 1 failed / 5 skipped, and the failure is those two
  missing `/usr/bin` wrappers. **Identical at baseline** — verified in a
  detached worktree at HEAD. Live-system state, not a regression.
- **`workout_locker` reports error** in `check_and_enable_services.sh`. That is
  the separate `screen-locker` repo.
- **`syncyomi-guard` is red** since 00:00 on 2026-08-23, working as designed:
  the library collapsed from 2185 manga to 8. See the
  `syncyomi-restore-silent-partial` memory; do NOT checkpoint the WAL before
  recovering. Newest snapshot: `~/syncyomi/snapshots/`, 2026-08-15.

## Traps worth keeping

- **Filter history on every path a unit has EVER lived at.** `hosts` had 1
  commit at its current path and 51 across four roots; `digital_wellbeing` had
  2 and 63 across three. A single `--path` truncates history to the last move
  and `git log | head` looks perfectly fine afterwards.
- **A unit's tests may not live beside it.** Six suites for `digital_wellbeing`
  sat in `linux_configuration/tests/`, and five of them ran in CI's Arch
  container. Moving code without them leaves tests exercising code that is
  gone, and leaves their names in `shell-tests.yml`'s hardcoded arrays.
- **Run the caller; do not read it.** `shellcheck` and `grep` both passed
  `check_and_enable_services.sh` while `DW_REPO` was used 30 lines above its
  definition. `dns-blocklist-refresh.service` likewise only revealed
  `/root/hosts-blocker` when actually started — under systemd there is no
  `SUDO_USER` and `id -un` is `root`.
- **`$HOME` is the wrong question.** Use `SUDO_USER`'s passwd entry; fall back
  to the owner of the file itself when running as bare root. That is what
  `linux_configuration/lib/extracted_repos.sh` does.
- **A shrinking denominator can break a duplication gate.** Removing 80 files
  pushed jscpd to 2.09% on clones this session never touched — inside the
  _generated_ `.ci-mirror-venv/`, which jscpd scanned because it walks the
  working tree, not the index.
- **A guarded check that skips is worse than one that fails.** Several of these
  defects survived months because the code said `if [[ -f $x ]]` and quietly
  did nothing when `$x` had moved.
- **`.pre-commit-config.yaml` is NOT a symlink**, unlike `pyproject.toml`,
  `run.sh`, `requirements.txt`, `lint_python.sh` and `.fvmrc`. Do not "sync" it
  with `meta/.pre-commit-config.yaml`; they are deliberately different.
- **Never raise the 2G pytest cap** on a "tests passed, then Killed" push —
  that is the ci-mirror concurrency issue, already fixed by
  `should_serialise_gates`.
- **A red `main` deadlocks its own fix.** `CI_GREEN_SKIP=1` must be set on the
  **push**, not the commit, and only when the push really is the fix.

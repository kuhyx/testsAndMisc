# testsAndMisc restructure — where it stands

Plan: `~/.claude/plans/after-refactor-of-testsandmisc-modular-wigderson.md`
Live-state checklist: `docs/restructure-live-state.md`
(regenerate with `./meta/scripts/report_live_state.sh`)

## Verified state as of 2026-08-23 (all pushed, `main` clean)

```
depth violations   46   (41 digital_wellbeing + 5 hosts — nothing else)
source files     1051 / 1200 ceiling
tracked files    1346   (2295 at the start, 1993 before the prune)
```

Both gates are wired and run on every commit. The depth gate runs `--warn`
because the only paths left over the cap are the two units below. **Delete
`--warn` from the `directory-depth-cap` hook entry in `.pre-commit-config.yaml`
once BOTH units are out, and the cap enforces for real.**

## Done

**Archived** to `github.com/kuhyx/testsAndMisc-archive`, full history:
`bucket_catch`, `poker-stakes`, `billsplit`.

**Extracted** to public repos, full history: `reverse-survivors`,
`kcd2-dice-solver` (`~/kcd2-dice-solver`), `focus-owner` (**no local clone —
GitHub only**), `mtk-root`, `system-maintenance` (`~/system-maintenance`),
`android-guardian` (`~/android-guardian`), `phone-focus-mode`.

**Flattened.** `linux_configuration/scripts/` and `single_use/` are gone.

**Gates wired.** 57 structural depth violations exempted (whole projects `C/`,
`dwm/`, `artgate/`; a module-split tool; prose trees; and the five
format-dictated segments `systemd`/`hooks`/`workflows`/`patches`/`fixtures`).
`check_repo_size.sh` counts tracked source files and caps the bookkeeping dirs
at 60 each, with `--prune` to clear them.

**Pruned** 655 superpowers artifacts (695 → 40 + 2 templates).

**Guard repoint DONE on the host.** Both guards now name
`/usr/local/share/guard-lib-plugins/`, re-enforced, target files byte-identical
by md5, DNS verified between them. Backups at
`/var/tmp/{resolved.conf,nsswitch.conf}.pre-repoint`.

## Remaining

1. **`hosts` extraction — do this first; everything else is optional.**
   Now unblocked: the guards no longer name a repo path. Its installer was
   already proven in vmbox to run from an extracted layout. 5 depth violations
   live here.

2. **`digital_wellbeing` — last, and the hardest.** 41 depth violations.
   Owns the pacman wrapper, `chattr +i`, `heavy_job_lock.sh`, and 12
   orchestrator paths in `check_and_enable_services.sh` /
   `setup_periodic_system.sh` that were already rewritten once by the flatten
   and will need it again. Also owns
   `linux_configuration/tests/test_shutdown_timer_monitor.sh`.
   `setup_midnight_shutdown.sh` is `chattr +i` and is excluded from two
   pre-commit fixer hooks by path — that exclude must move with it.

3. **Nextcloud dedup — recommended AGAINST, with numbers.** Not a filename
   grep: `grep -rln -i nextcloud linux_configuration/` finds **3,618 lines
   across 22 files** (566 entry points + 2,383 libs + 604 tests). The two lib
   families `nc_*` (1212 lines) and `rpi_nc_*` (1171) are parallel
   _evolutions_, not copies — all four shared function names differ in body,
   not just comments. Only **3 of 15 libs have tests**, and the target is a
   remote Raspberry Pi that cannot be tested against from here. Do not attempt
   without hardware access.

4. **`.hippo/` — dead, awaiting a decision.** 161 tracked files, 3.2M. All 158
   episodic entries have `retrieval_count: 0`, 22 self-tag `invalidated`, last
   write 2026-05-28, the tool is uninstalled, nothing references it.
   Untracking needs a new `.gitignore` entry — `hippo.db` is currently
   untracked only because `*.db` is ignored. **Ask before deleting.**

5. **3.7 GB of extraction residue**, untracked: `focus_owner/` (3.2G),
   `bucket_catch/` (303M), `kcd2_dice_solver/` (149M), `billsplit/` (62M).
   None has a `.git`. The only non-build files are `.idea/` IDE config and a
   Flutter-_generated_ `GeneratedPluginRegistrant.java` — no hand-written
   source. Repos are safe on GitHub. **Ask before `rm -rf`.**

6. **8 stale live-system references** (pre-existing, from the earlier flatten,
   NOT from the gate work). `./meta/scripts/report_live_state.sh --check`
   lists them; they name `linux_configuration/scripts/...` paths that no
   longer exist. Two were the guard plugins, now fixed; the rest include
   `setup_dns_blocker.sh` and `organize_downloads.sh`.

## Traps already paid for

- **Run it, don't read it.** `--prune` sorted on `%cs` (date only), which ties
  every same-day artifact; `sort` fell back to the path and it deleted
  _alphabetically_, picking one of the newest files. Invisible in review.
  Use `%ct` + `sort -rn`. Test destructive modes in a detached worktree.
- **A filename grep undercounts a capability 7x.** `git ls-files | grep -i X`
  matches names only and misses the `lib/` layer, where the bulk lives.
  Use `grep -rln` over contents before calling an estimate stale.
- **"Tests passed, then Killed" is not a test failure.** ci-mirror ran
  `pre-commit --all-files` (~1.75 GiB) and pytest (~0.29 GiB) concurrently;
  the pytest scope has `MemorySwapMax=0`, so it was the one killed. Fixed by
  `should_serialise_gates` in `meta/scripts/ci_mirror_mem.sh`. **Never raise
  the 2G cap** — measure what runs alongside. `/usr/bin/time -v` hides this
  (it measures only the parent); read `memory.peak` from a cgroup.
- **`sudo -n` works here and `guardctl` is at `/usr/local/bin/guardctl`.** The
  old "the classifier blocks me" note was stale.
- **A red `main` deadlocks its own fix.** `ci-baseline-green` refuses to build
  on a red baseline, and ci-mirror runs `pre-commit` inside a clean worktree,
  so the hook fires there too — the commit that FIXES the red baseline cannot
  be pushed. `CI_GREEN_SKIP=1` must be set on the **push**, not just the
  commit: `CI_GREEN_SKIP=1 git push`. Use it only when the push really is the
  fix.
- **The pre-push gate is not the pre-commit gate.** It adds prettier and
  ci-mirror. Two docs were non-conforming before this session and blocked
  _every_ push; prettier normalises `*emphasis*` to `_emphasis_`.
- **`.pre-commit-config.yaml` is NOT a symlink** (unlike `pyproject.toml`,
  `run.sh`, `requirements.txt`, `lint_python.sh`, `.fvmrc`). The root file is
  the active config; `meta/.pre-commit-config.yaml` is a separate standalone
  variant, already ~219 lines divergent. Do not "sync" them.
- **`/usr/local/bin` holds copies naming repo paths** — invisible to a repo
  grep. `report_live_state.sh` scans there.
- **Path rewrites need resolving, not reviewing.** Relative `source` depths
  differ per file, and a test can hardcode a prefix the script no longer uses
  — `test_music_parallelism.sh` failed a layout that was correct.
- **Sourcing top-level code is not a split.** boot-repair's report block has
  `exit` calls; moving it broke 30 of 42 tests.

## Unrelated: syncyomi-guard is red

Failing since 00:00 on 2026-08-23, working as designed: the library collapsed
from 2185 manga / 68902 chapters to 8 / 895. See the
`syncyomi-restore-silent-partial` memory; do NOT checkpoint the WAL before
recovering. Newest snapshot in `~/syncyomi/snapshots/` is 2026-08-15.

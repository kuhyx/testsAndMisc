# testsAndMisc restructure — where it stands

Plan: `~/.claude/plans/after-refactor-of-testsandmisc-modular-wigderson.md`
Live-state checklist: `docs/restructure-live-state.md`
(regenerate with `./meta/scripts/report_live_state.sh`)

## Done

**Archived** to `github.com/kuhyx/testsAndMisc-archive`, full history:
`bucket_catch`, `poker-stakes`, `billsplit` (+ `python_pkg/billsplit_coverage`,
its CI workflow, the `app_icons` registry entry, and the paired
`.binary-allowlist` / `.gitignore` icon rules — `.binary-allowlist` now has no
patterns at all).

**Extracted** to public repos, full history, each with CI it did not have here:
`reverse-survivors`, `kcd2-dice-solver` (`~/kcd2-dice-solver`), `focus-owner`,
`mtk-root`, `system-maintenance` (`~/system-maintenance`), `android-guardian`
(`~/android-guardian`), `phone-focus-mode` (with `python_pkg/focus_policy`).

**Flattened.** `linux_configuration/scripts/` and `single_use/` are gone;
categories sit directly under `linux_configuration/`. `i3-configuration` moved
out of `periodic_background` into `i3/` + `i3blocks/`, and
`misc/testsAndMisc-bash/` lost its redundant nesting.

**Length cap widened** to catch extensionless scripts, and `boot-repair` split
756 → 218 with four libs.

Depth violations **556 → 104**; tracked files **2295 → ~1980**. Every commit
green; nothing used `--no-verify`.

## Remaining

1. **The guard repoint** (deferred at your request). Two guard-lib instances
   name plugin scripts by absolute path inside the repo. Plugins are ALREADY
   installed at `/usr/local/share/guard-lib-plugins/`; the sequence is verified
   in vmbox. The classifier blocks me from running it:

   ```
   sudo guardctl file-guard uninstall resolved --keep-canonical
   sudo guardctl file-guard install resolved --target /etc/systemd/resolved.conf \
     --plugin /usr/local/share/guard-lib-plugins/resolved-plugin.sh \
     --also-watch /etc/systemd/resolved.conf.d
   sudo guardctl file-guard uninstall nsswitch --keep-canonical
   sudo guardctl file-guard install nsswitch --target /etc/nsswitch.conf \
     --plugin /usr/local/share/guard-lib-plugins/nsswitch-plugin.sh
   sudo guardctl file-guard enforce resolved && sudo guardctl file-guard enforce nsswitch
   ```

2. `hosts` extraction — blocked on (1). Its installer was already proven in
   vmbox to run from an extracted layout with no monorepo path.
3. `digital_wellbeing` **last** — pacman wrapper, `chattr +i`, `heavy_job_lock.sh`
   (moved in with it), and the 12 orchestrator paths in
   `check_and_enable_services.sh` / `setup_periodic_system.sh`, which now point
   at the NEW locations and will need updating again when it moves. It also owns
   `linux_configuration/tests/test_shutdown_timer_monitor.sh`.
4. ~~Wire the gates.~~ **DONE.** The 57 structural violations are exempted
   and both gates run on every commit. The depth gate runs `--warn`, because
   the only 47 paths left over the cap are the ones (2) and (3) will remove;
   drop `--warn` as the last step of those extractions and the cap enforces
   for real. `check_repo_size.sh` counts tracked source files (1049/1200) and
   also caps the bookkeeping dirs at 60 each.
5. ~~Prune `docs/superpowers/evidence|contracts`.~~ **DONE** — 655 removed,
   newest 20 of each kept, tracked files 1993 → 1340. Nothing reads the
   corpus; git history keeps it. `.hippo/` is **decided but not executed**:
   all 158 entries have `retrieval_count: 0`, 22 self-tag `invalidated`, the
   last write was 2026-05-28, `hippo.db` is untracked and the tool is
   uninstalled. It is dead; awaiting the untrack-vs-delete call.
6. **Recommended against**, with numbers. The estimate was right (~3,600 lines
   across 22 files — a filename grep finds only 400 of them), but the two
   `nc_*` (1212 lines) and `rpi_nc_*` (1171 lines) lib families are parallel
   *evolutions*, not copies: all four shared function names differ in body,
   not just comments. Only 3 of 15 libs have tests, and the target is a remote
   Raspberry Pi that cannot be tested against from here. Merging is a
   regression risk out of proportion to an optional cleanup.

7. **3.7 GB of extraction residue**, untracked and unreported until now:
   `focus_owner/` (3.2G), `bucket_catch/` (303M), `kcd2_dice_solver/` (149M),
   `billsplit/` (62M). None has a `.git`; each holds **zero** source files
   outside `build/`, `node_modules/`, `dist/` and `coverage/`. The real repos
   are on GitHub and were pushed 2026-08-23, so this is pure build output —
   `rm -rf` on the user's say-so. Note `focus-owner` has no local clone at
   `~/focus-owner`; only the GitHub copy exists.

## Traps already paid for

- **Run it, don't read it.** Repointing kcd2 hit three failures in a row (pnpm
  ignoring the `package.json` field, no-TTY `node_modules` purge, a Docker mount
  on the deleted path). `dice.kuhy.duckdns.org` now serves from the new repo.
- **`/usr/local/bin` holds copies naming repo paths** — invisible to a repo grep.
  `report_live_state.sh` scans there now.
- **Removing a file can break a suite that stays** (`mtk_harness.sh`), and a
  removal can silently shrink CI (`shell-tests.yml` uses TWO hand-maintained
  lists plus a glob — check all three).
- **Never let a test fall back to `/usr/local/bin`**: the installed copy can be
  stale, and the test then compares against a binary it never generated.
- **pre-commit's patch restore can revert an edit** made before the commit. The
  `app_icons` and `AGENTS.md` changes each had to be applied twice.
- **Path rewrites need resolving, not reviewing.** Relative `source` depths
  differ per file (`../../` vs `../../../`), `REPO_ROOT` walks a fixed number of
  levels, `$VAR/scripts/...` prefixes hide from a naive regex, and
  `# shellcheck source=` directives break independently of the code.
- **Sourcing top-level code is not a split.** boot-repair's report block has
  `exit` calls; moving it broke 30 of 42 tests.

## Unrelated: syncyomi-guard is red

Failing since 00:00 on 2026-08-23, ~17h before this work started. It is working
as designed: the library collapsed from 2185 manga / 68902 chapters to 8 / 895.
See the `syncyomi-restore-silent-partial` memory; do NOT checkpoint the WAL
before recovering. Newest snapshot in `~/syncyomi/snapshots/` is 2026-08-15.

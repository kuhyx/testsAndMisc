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
`reverse-survivors`, `kcd2-dice-solver` (cloned to `~/kcd2-dice-solver`),
`focus-owner`, `mtk-root` (took the four `mtk_*` libs and three suites that
lived in `scripts/lib/`).

**Gates written, deliberately NOT wired**: `meta/scripts/check_directory_depth.sh`
(cap 2; exempts `third_party/`, `docs/superpowers/`, `.github/skills/` by prefix
and `lib/` / `tests/` by path segment). Violations 556 → 294.

Depth, tests and pre-commit verified green at every commit; nothing used
`--no-verify`.

## Decisions taken this session

- **Depth cap is 2**, with `lib/` and `tests/` exempt — so the ~118 single_use
  lib files stay put and step D only flattens entry scripts.
- **`meta/` is in scope** for the cap.
- **`scripts/lib/common.sh` STAYS.** Measured: 55 consumers, 51 of which remain
  here. The `.githooks` use a _separate_ `common.sh`, so the ">2 units" rule
  selects nothing worth moving. Deviation from the original instruction,
  agreed after measurement.
- **`periodic_background/lib/` STAYS** — 9 files, one consumer
  (`check_and_enable_services.sh`), not a shared library.
- New repos are **public**; vmbox pass required for **all four** subsystems.

## Remaining, in order

1. `system-maintenance` — no cross-unit source edges.
2. `android_guardian` (`periodic_background/utils/`) — settle
   `heavy_job_lock.sh`. The seam is already clean: consumers read the
   _installed_ `/usr/local/bin/heavy_job_lock.sh` and
   `meta/scripts/run_with_heavy_lock.sh` documents a "missing lock ⇒ run
   unserialised" fallback.
3. `hosts` — owns `/etc/guard-lib/targets/{resolved,nsswitch}.conf` plugin
   paths. Confirm `guardctl status` after, not just that files moved.
4. `phone_focus_mode` + `python_pkg/focus_policy` — must come after `hosts`:
   `deploy_phases.sh:73` executes hosts' `generate_hosts_file.sh`.
5. `digital_wellbeing` **last** — pacman wrapper, `chattr +i`, and the 12
   hardcoded orchestrator paths in `check_and_enable_services.sh:61-74` /
   `setup_periodic_system.sh:20-23`.
6. Step D: flatten the 207 remaining entry-script violations
   (`single_use/**` is ~130 of them). Deduplicate the two Nextcloud
   implementations first — ~2,780 lines for one capability.
7. Step E: wire both gates, close the `boot-repair` hole (756 lines, escapes
   the 250-line cap because `is_source_file()` needs a dot in the filename),
   prune `docs/superpowers/` churn.

## Traps already paid for

- **Run the thing, don't read it.** Repointing kcd2 surfaced three failures no
  grep would have found: pnpm ignoring the `package.json` "pnpm" field, pnpm
  refusing to purge `node_modules` without a TTY, and the Docker container
  still bind-mounting the deleted monorepo path.
- **`/usr/local/bin` holds copies that name repo paths** — invisible to a repo
  grep, and `periodic-system-maintenance.sh` runs hourly with three such paths
  into digital_wellbeing and hosts. Any extraction of those two must
  _reinstall_ it, not just edit the repo copy.
- **Removing a file can break a suite that stays.** Deleting `mtk_harness.sh`
  broke `test_common_datetime.sh`, which sources it. Check both directions.
- **pre-commit's patch restore can silently revert an edit** made before the
  commit — the `app_icons` change had to be applied twice. Re-grep after
  committing.
- `shell-tests.yml` discovers suites by glob, so a removal shrinks CI coverage
  with a green build. Record the suite count before and after.

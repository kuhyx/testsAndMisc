# Next session prompt — testsAndMisc restructure, final units

Paste everything below into a fresh session.

---

Extract `linux_configuration/periodic_background/hosts/` into its own repo,
then `digital_wellbeing/`. Read `NEXT_SESSION_RESTRUCTURE.md` first — its
"Traps already paid for" section is the expensive part and every line in it
cost a real failure.

## Start here

```bash
cd ~/testsAndMisc
./meta/scripts/check_directory_depth.sh --all | head -1   # expect 46
./meta/scripts/check_repo_size.sh                         # expect 1051/1200
git status -sb                                            # expect clean
```

If those three numbers do not match, something moved since 2026-08-23 —
find out what before extracting anything.

## What to do

**1. `hosts` first** (5 depth violations). It is unblocked: the guard repoint
landed on 2026-08-23, so no guard names a repo path any more
(`sudo guardctl file-guard status resolved` should print
`/usr/local/share/guard-lib-plugins/...`). Its installer was already proven in
vmbox to run from an extracted layout.

**2. `digital_wellbeing` last** (41 violations). The hard one. It owns the
pacman wrapper, `chattr +i`, `heavy_job_lock.sh`, and 12 orchestrator paths in
`check_and_enable_services.sh` / `setup_periodic_system.sh` that the flatten
already rewrote once. `setup_midnight_shutdown.sh` is `chattr +i` and is
excluded from two pre-commit fixer hooks **by path** — that exclude must move
with it, or the next commit fails on a file nothing can write.

**3. Then close the loop:** delete `--warn` from the `directory-depth-cap` hook
entry in `.pre-commit-config.yaml`. That is the whole point of the campaign —
the cap only enforces once both units are gone. Verify with
`./meta/scripts/check_directory_depth.sh --all` exiting 0.

## Constraints

- Use the `extract-to-own-repo` skill; do not hand-roll the mechanics.
- **Sandbox-first**: both units are root/`/etc`/systemd/pacman territory, so
  vmbox before the host (`vmbox-testing` skill). A vmbox pass never proves the
  host is fine — report it as "passed in vmbox, not verified on the host".
- Never `--no-verify`. Every commit in this campaign has been green.
- `sudo -n` works and `guardctl` is at `/usr/local/bin/guardctl` — do not
  hand me commands you can run yourself.
- Run `./meta/scripts/report_live_state.sh --check` **before and after** each
  move. It scans `/usr/local/bin` too, where installed copies name repo paths
  invisibly to a repo grep. There are already 8 known-stale references from the
  earlier flatten; do not add more.
- Each commit needs an evidence artifact; 4+ staged code files (`.sh` counts,
  `.json`/`.yaml` do not) also needs a contract.

## Ask before doing (do not decide these yourself)

- deleting `.hippo/` (161 tracked files; dead since 2026-05-28, but it is a
  deletion)
- `rm -rf` on the 3.7 GB of untracked extraction residue (`focus_owner/`,
  `bucket_catch/`, `kcd2_dice_solver/`, `billsplit/`)

## Do NOT

- attempt the Nextcloud dedup — measured and recommended against; it needs a
  Raspberry Pi that cannot be reached from here, and only 3 of 15 libs have
  tests. See item 3 of the status doc for the numbers.
- raise the 2G pytest cap if the push fails with "tests passed, then Killed".
  That is the ci-mirror concurrency issue, already fixed; measure what runs
  alongside instead.
- "sync" `.pre-commit-config.yaml` with `meta/.pre-commit-config.yaml`. They
  are deliberately different files.

## Done means

`./meta/scripts/check_directory_depth.sh --all` exits **0** with `--warn`
removed from the hook, both units are their own repos with CI, the live-state
check adds no new stale references, and `main` is pushed clean.

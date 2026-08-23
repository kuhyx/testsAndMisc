# Next session: make `install_core_system.sh` actually work on a fresh machine

Paste everything below into a **fresh** Claude session (`/clear` first).

---

`~/testsAndMisc/linux_configuration/install_core_system.sh` is the documented
way to set this machine up from scratch. It does not work. Three defects were
found on 2026-08-22 by running the real installer in a disposable Arch VM
(`~/utils/vmbox`) rather than by reading it — 2 of its 7 modules cannot install
at all, and a third installs something that silently does nothing.

**Do not trust this file's line numbers without re-checking them.** They were
correct on 2026-08-22; the repo moves.

## The evidence

The sandbox progression, measured with the repo's own hardening checks:

| State | Result |
|---|---|
| Bare guest, nothing installed | 0 passed / 17 skipped |
| After `install_core_system.sh --all` | 10 passed / 14 skipped |
| After manually installing guard-lib + the shutdown timer | 14 passed / 10 skipped |
| After manually running the hosts migration | **18 passed, 6 skipped, 0 failed** |

The remaining 6 skips are legitimately screen_locker's. The gap between row 2
and row 4 is entirely defects 2 and 3 below: everything needed to reach a green
machine already exists in the repos, but the documented install path never runs it.

## Defect 1 — two module paths no longer exist

`install_core_system.sh` invokes:

- line 129: `bash "$REPO_ROOT/python_pkg/screen_locker/install_systemd.sh"` — **gone**
- line 143: `sudo bash "$REPO_ROOT/python_pkg/steam_backlog_enforcer/install.sh"` — **gone**

Both packages were extracted into their own repos. Verified on disk 2026-08-22:

- `~/screen-locker/install_systemd.sh` (5637 b, executable)
- `~/steam-backlog-enforcer/install.sh` (3248 b, executable)

"Workout screen locker" is a **CORE** module, so a fresh machine fails on the
first thing the installer does.

Note this makes the installer **cross-repo**: `~/testsAndMisc` no longer owns
that code. That is design question (b) below — do not just hardcode `~/screen-locker`
and call it done without putting the question to kuhy.

## Defect 2 — guard-lib is required but never installed

`scripts/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh`
depends on `guardctl` and dies with `guardctl not found on PATH`. Nothing in
`install_core_system.sh` installs guard-lib, which lives at
`~/utils/guard-lib/install.sh` — a **third** sibling repo.

So the CORE module "Midnight shutdown timer" always fails on a fresh machine.

## Defect 3 — the hosts file-guards are installed only by a one-shot script

`scripts/periodic_background/hosts/install.sh` (130 lines) never installs the
hosts/nsswitch/resolved file-guards. Its own comment block around **line 109**
claims otherwise:

> Enforcement does not depend on these sources being immutable: /etc/hosts
> itself is chattr +i, guard-lib's "hosts" file-guard instance (`guardctl
> file-guard status hosts`) watches and re-enforces it against its canonical
> snapshot, and the same instance's bind mount pins it.

That is only true after running
`scripts/single_use/fixes/migrate_hosts_guard_to_guard_lib.sh` (169 lines),
which is filed under `single_use/fixes/` and is not part of any install path.

A fresh machine following the documented path therefore gets `chattr +i` and
**no watcher, no canonical copy, no bind mount** — immutability with nothing
re-enforcing it. Verified both ways in the sandbox: 5 hardening checks stayed
skipped until the migration was run, then passed.

## Two design questions — ask kuhy, do not guess

Run these as a `grilling` round before writing any code.

**(a) Where should defect 3's fix live?** Either `hosts/install.sh` calls the
migration script, or the migration's logic moves into `install.sh` and the
one-shot script is deleted (or becomes a thin wrapper). The first is a smaller
diff; the second stops `single_use/fixes/` from being load-bearing, which is
arguably what "single use" is supposed to mean.

**(b) How should a testsAndMisc installer reach code in sibling repos?**
`~/screen-locker`, `~/steam-backlog-enforcer` and `~/utils/guard-lib` are
separate repos now. Options, none obviously right:

1. **Expect-adjacent** — check for `~/screen-locker` etc., fail with a clear
   message naming the repo to clone. Simple; the installer stops being
   self-contained.
2. **Clone if missing** — the installer clones the siblings it needs. Works on
   a truly bare machine; puts network access and repo URLs into an installer
   that currently has neither.
3. **Drop those modules** — `install_core_system.sh` installs only what
   testsAndMisc owns, and each sibling repo installs itself. Cleanest ownership;
   means there is no longer one command that sets up the machine.
4. **Invert entirely** — a top-level bootstrap outside all four repos.

Do not assume `~/` layout is stable; whatever is chosen must fail loudly with
an actionable message rather than silently skipping a module.

## Done — checkable in a sandbox, not a sentence

The fix is done when, in a **fresh** vmbox guest:

```bash
vm share ~/testsAndMisc && vm share ~/utils
vm new inst
vm run inst 'git clone --no-hardlinks -q /mnt/hostrepo/testsAndMisc ~/tam'
# plus whatever cloning question (b)'s answer implies for the sibling repos
vm run inst 'cd ~/tam && echo y | bash linux_configuration/install_core_system.sh --all'
```

1. Every module reports installed or **explicitly** skipped with a reason —
   zero entries in the installer's own `Failed (...)` summary section.
2. The hardening checks reach **18 passed, 6 skipped, 0 failed**, matching the
   row-4 measurement above, with **no manual steps after the installer**.
   The 6 skips must be the screen_locker ones; if a different 6 skip, that is
   a regression, not a pass.
3. `guardctl file-guard status hosts` in the guest shows a live watcher with a
   canonical copy and a bind mount — not just `chattr +i` on `/etc/hosts`.
4. Re-running the installer a second time is a no-op that still exits 0
   (it must be idempotent; the sandbox makes this cheap to check).

## How to work on this

- **Sandbox first, always.** This is a root installer that writes `/etc`,
  systemd units, pacman hooks and `chattr +i`. Never run it on the host to
  test it. `~/utils/vmbox`: `vm new` / `vm run` / `vm reset`. A sandbox pass
  does **not** prove the host is fine — report it that way.
- Installers prompt; `vm run` closes stdin, so pipe `echo y |`.
- vmbox is fast: `vm run` ~14s cold / ~3s warm, `vm reset` ~2s. Reuse one
  sandbox, do not rebuild per command.
- `~/utils/vmbox/SESSION_RESULTS.md` has the full 2026-08-22 measurements.
- The 250-line file cap applies (`~/utils/file_length`). `install.sh` is at
  130 lines and the migration at 169 — merging them wholesale will breach it,
  which is worth weighing in design question (a).
- `~/testsAndMisc` requires a `docs/superpowers/evidence/*.json` artifact for
  any code change (pre-commit gate `ai-evidence-contract`); copy
  `docs/superpowers/evidence/template.json`.

## Out of scope

Do not fix `boot-repair` — its BIOS/GRUB guard landed 2026-08-22 in commit
`aec2b275`. Do not refactor the installer's module-runner machinery
(`run_installer` / `ask_install`); the defects are all in what it points at.

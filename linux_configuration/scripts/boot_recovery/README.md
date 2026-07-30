# boot-repair

Offline recovery for a stale EFI System Partition — the failure that dropped
this laptop into emergency mode on 2026-07-30.

## The failure it fixes

A kernel upgrade replaced `/usr/lib/modules/<old>` with `<new>`, but the new
kernel image never reached the ESP. The firmware kept booting the **old**
`vmlinuz`, whose module tree no longer existed, so nothing modular could load
after pivot-root. `vfat` was among the casualties — which meant `/boot` itself
could not be mounted, `local-fs.target` failed, and systemd dropped to
emergency mode. pacman reported the upgrade as successful.

**Root cause on this machine:** `pacman-git` with `ParallelDownloads > 1` makes
every forked alpm hook child segfault (SIGSEGV in libc), silently skipping
`90-mkinitcpio-install` and `depmod`.

## Install

```bash
sudo ./install.sh
```

Installs:

| Path | Purpose |
|---|---|
| `/usr/local/sbin/boot-repair` | the repair tool |
| `/etc/pacman.d/hooks/05-boot-mounted-guard.hook` | pre-transaction **gate** |
| `/etc/pacman.d/hooks/99-boot-autorepair.hook` | post-transaction auto-repair |

It lives on the **root** filesystem by necessity: the ESP is unreachable by
definition when this is needed.

## Use

```bash
sudo boot-repair              # repair now (default)
sudo boot-repair --dry-run    # report only, change nothing
```

From the systemd emergency shell the root filesystem is already mounted, so:

```
/usr/local/sbin/boot-repair
```

No network is used at any point. Missing kernel modules are recovered from
`/var/cache/pacman/pkg`.

### Options

| Flag | Meaning |
|---|---|
| `--dry-run` | Report problems, change nothing |
| `--preflight` | Exit non-zero unless the ESP is mounted (used by the gate hook) |
| `--auto` | Quiet repair for the post-transaction hook |
| `--root DIR` | Operate on another root (fixtures, or an Arch ISO chroot) |
| `--esp DEVICE` | Override ESP auto-detection |

Exit status: `0` consistent/repaired, `1` problems remain, `2` usage error.

## What it checks and repairs

1. Root filesystem read-only after a failed boot → remount rw
2. `noauto`/`nofail` on `/boot` in fstab → reset to `defaults` (backed up).
   `nofail` turns a loud emergency drop into a *silent* boot of a stale kernel,
   which is strictly worse.
3. Orphaned kernel files written into the unmounted `/boot` → delete
4. `vfat` unloadable → restore `fs/fat` + `fs/nls` from the cached kernel
   package, `depmod`, `modprobe`
5. ESP not mounted → mount it
6. Missing `modules.dep` → `depmod`
7. ESP kernel ≠ newest complete module tree → install the kernel
8. initramfs ≠ that kernel → `mkinitcpio -P`
9. `ParallelDownloads > 1` → set to `1` (the root cause)

A module tree counts as usable only if it has **both** `vmlinuz` and `kernel/`.
The wreckage this bug leaves behind is a directory holding only `modules.*`
metadata, and a naive "newest directory" pick would choose it.

## Safety invariants

- Files under `/boot` are deleted **only** while it is not a mountpoint **and**
  contains no `EFI/` or `loader/`. Deleting after mounting would destroy the
  real kernel.
- `EFI/` and `loader/` are never written or removed.
- The running kernel's module tree is never deleted.
- No network, ever.

## Tests

```bash
./tests/test_boot_repair.sh     # 31 fixture tests, no root needed
sudo ./tests/live_test.sh       # 11 live tests, reversible
```

`live_test.sh` refuses to start unless the system is already consistent, and an
EXIT trap remounts the ESP however it ends. It covers what fixtures cannot:
the pre-transaction gate, unmounting the real ESP, and deleting shadow files
off the real root filesystem while proving the ESP survives.

### Verified behaviour

- 31/31 fixture tests, 11/11 live tests, `shellcheck` clean
- Gate proven to abort a real kernel transaction with the ESP unmounted:
  `error: failed to commit transaction`, *no packages upgraded*, nothing
  written into the unmounted `/boot`

## Limitation

If the running kernel's package is not in `/var/cache/pacman/pkg`, step 4 is
impossible offline. The script says so and prints the Arch-ISO chroot recovery
commands rather than guessing.

# Phone Focus Mode Skill

## Overview

Focus mode is a geofence-based attention tool for a Magisk-rooted Blackview BL9000 (MTK MT6891).
When the phone is at home it enters focus mode: distracting apps are disabled and domain blocking
is enforced. Outside home, the phone returns to normal.

Scripts live in `phone_focus_mode/`. Deployment: `deploy.sh <phone_ip>` or
`ADB_SERIAL=<serial> deploy.sh`.

---

## Critical: Things That Will Brick / Factory-Wipe the Phone

### DO NOT use `pm uninstall -k --user 0` or `pm disable-user` on SYSTEM apps

MediaTek ROMs (and many others) trigger Android recovery / factory wipe on next boot when their
package manager scan finds system packages missing or disabled. This happened multiple times.

- `pm uninstall -k --user 0` → removes package from user-0 registry → survives reboot → wipe
- `pm disable-user --user 0` on system packages → package state persists → wipe

**Safe approaches:**

- `pm disable-user --user 0` is safe for 3rd-party (non-system) apps only
- For system apps (YouTube, Chrome, Play Store) use **UID firewall rules** or **DNS/hosts blocking**
- Never put system package names in `BLOCKED_SYSTEM_APPS` unless you have a tested recovery path

`BLOCKED_SYSTEM_APPS` in `config.sh` should remain **empty string** (`""`).

---

## Hosts File Blocking

### The Problem: ROM's /system partition is truly read-only

This device's system partition cannot be remounted rw — even with Magisk root, `mount -o remount,rw /system`
silently fails. `/system/etc/hosts` does not exist (no inode).

### The Solution: Magisk Systemless Hosts module

Magisk ships a "Systemless Hosts" built-in module. When enabled in the Magisk app, it magic-mounts
any file under `/data/adb/modules/hosts/system/etc/hosts` as `/system/etc/hosts` at boot.

**Required one-time setup (user must do in Magisk app):**

1. Open Magisk app → Modules tab
2. Enable "Systemless Hosts" module (toggle)
3. Reboot

This must be done manually the first time (or after a factory reset). There is no way to enable it
programmatically via ADB without user interaction on some firmware versions — `magisk --sqlite`
approach exists but is unreliable across versions.

After enabling the module, `hosts_enforcer.sh` automatically keeps it in sync by copying the
canonical hosts file to `/data/adb/modules/hosts/system/etc/hosts` every `HOSTS_CHECK_INTERVAL`
seconds. This survives reboots.

### What hosts_enforcer.sh does

1. Watches `$HOSTS_CANONICAL` (pushed by `deploy.sh` from `linux_configuration/hosts/`)
2. Copies it to `/data/adb/modules/hosts/system/etc/hosts` (Magisk module path)
3. Falls back to bind-mount / direct overwrite of `/system/etc/hosts` if it exists
4. Verifies integrity and re-syncs if tampered

### Domains blocked

Uses StevenBlack hosts with fakenews/gambling/porn/social extensions (~171k domains).
Custom YouTube/social entries in `DNS_BLOCK_HOSTS` config var. All apps including browsers
are blocked from resolving these domains — not just the YouTube app.

---

## App Blocking Strategy

### UID-based firewall (dns_enforcer.sh)

For system apps that cannot be safely disabled via `pm`, UID-based iptables rules block
web access (ports 80/443 only — DNS port 53 is deliberately NOT blocked).

**CRITICAL: Only block ports 80/443, NEVER all TCP/UDP for an UID.**
Blocking all TCP/UDP for a UID also kills DNS for that process and (on some Android versions)
breaks the system DNS cache for other apps too, making the entire phone unable to load any website.

### Focus-mode-only vs always-blocked

- `DNS_BLOCK_PACKAGES_ALWAYS`: YouTube, YouTube Music, Chrome — always blocked
- `DNS_BLOCK_PACKAGES_FOCUS_ONLY`: Play Store — blocked only during focus mode

`dns_enforcer.sh` reads `$MODE_FILE` (current_mode.txt) every `DNS_CHECK_INTERVAL` seconds
and adds/removes focus-only UIDs accordingly.

### Play Store + Aurora Store

Play Store (com.android.vending) is blocked during focus mode via UID rules.
Outside focus mode it's accessible normally.

**Aurora Store** (`com.aurora.store`) is an open-source Play Store client that works without a
Google account. Install it via: `deploy.sh <ip> --install-aurora`. It lets you install any
app from the Play Store catalog without needing Play Store's network access during focus mode
(though Play Store is accessible outside focus mode anyway).

---

## Boot Autostart

`FOCUS_BOOT_AUTOSTART=1` in `config.sh` installs `/data/adb/service.d/99-focus-mode.sh`.

`magisk_service.sh` (the service.d entry point):

- Polls `sys.boot_completed` (max 180 seconds)
- Waits `FOCUS_BOOT_DELAY_SECONDS` (max 10 seconds)
- Checks for emergency disable marker: `$STATE_DIR/disable_boot_autostart`
- Starts hosts_enforcer, dns_enforcer, focus_daemon in order

**Known issue**: `dirname "$0"` is wrong from service.d context (points to service.d, not the scripts).
`magisk_service.sh` exports `FOCUS_MODE_SCRIPT_DIR=/data/local/tmp/focus_mode` before sourcing
`config.sh` to work around this. All scripts use `${FOCUS_MODE_SCRIPT_DIR:-$(cd "$(dirname "$0")" && pwd)}`.

---

## MTK-Specific Notes

- `pm disable-user` on system packages persists across reboots and can trigger factory wipe
- `mount -o remount,rw /system` silently fails (hardware read-only), use Magisk module approach
- ip6tables `--uid-owner` may fail with permission error from non-service.d su contexts; use `|| true`
- Boot sequence is slow on MTK; 180s wait for `sys.boot_completed` is appropriate

---

## ADB Root

Use `su --mount-master -c 'sh -s'` so that bind mounts propagate to the global namespace:

```bash
printf '%s\n' 'your commands here' | adb shell su --mount-master -c 'sh -s'
```

Without `--mount-master`, bind mounts are invisible to other processes (they only exist in the
su session's mount namespace).

---

## Testing

Unit tests: `phone_focus_mode/lib/tests/`

```bash
bash phone_focus_mode/lib/tests/test_magisk_service.sh   # 11 tests
bash phone_focus_mode/lib/tests/test_dns_enforcer.sh     # 5 tests
bash phone_focus_mode/lib/tests/test_hosts_enforcer.sh   # (create if needed)
```

Pre-commit: `pre-commit run --files phone_focus_mode/...`

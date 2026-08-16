# Approved user experience, file layout and backup storage

## Approved user experience

The workflow must support three main operator experiences.

### Normal day

Running:

```bash
./scripts/run_all/run_phone.sh
```

must:

- detect the phone over USB or paired wireless ADB
- take or update a backup snapshot
- collect health and security status
- repair minor drift when safe to do so
- print a concise summary of what changed and any remaining warnings

### After a format

Running:

```bash
./scripts/run_all/run_phone.sh fresh-phone
```

must:

- reconnect to the rooted phone
- restore the security stack first
- restore launcher, APKs, selected app data, and configured user files
- validate that the hardening is active again
- list any unavoidable manual follow-up actions

### If something feels wrong

Running:

```bash
./scripts/run_all/run_phone.sh doctor
```

must:

- inspect the same security and health checks as monitoring mode
- attempt repair of common drift
- stop short of broad destructive restore operations
- clearly distinguish between repaired issues and unresolved issues

This “what do I run and when?” guidance must appear in both:

- the future `phone_focus_mode/README.md` updates
- the help/usage text inside the visible wrapper script and the underlying
  implementation script

## File layout

The visible entrypoint should live at the top level, while the implementation
stays with the phone project.

### Visible entrypoint

- `scripts/run_all/run_phone.sh`

Responsibilities:

- be easy to find and remember
- locate the repository root reliably
- forward arguments to the project-local implementation
- provide brief usage/help output for common flows

This script should stay thin and stable.

### Project-local implementation

- `phone_focus_mode/run_phone.sh`

Responsibilities:

- orchestrate detection, backup, monitoring, restore, and repair flows
- call or wrap `deploy.sh` rather than replacing it
- serve as the canonical implementation home for phone-specific logic

### Supporting libraries

- `phone_focus_mode/lib/adb_common.sh`
- `phone_focus_mode/lib/backup.sh`
- `phone_focus_mode/lib/restore.sh`
- `phone_focus_mode/lib/monitor.sh`

Responsibilities:

- isolate common shell helpers into focused modules
- keep `run_phone.sh` readable and testable
- avoid duplicating fragile ADB, path, and parsing logic

### Declarative configuration

- `phone_focus_mode/backup_manifest.sh`

Responsibilities:

- define which packages should have APK snapshots
- define which app data locations should be captured
- define which media/user directories should be synced
- define health thresholds and alerting policy
- classify each restore target as safe, manual-only, or backup-only

This file should be the user-editable scope definition rather than burying
every backup decision in shell code. The manifest should be shell-native so
the implementation does not need a separate JSON parser dependency just to
load backup scope.

### PC automation assets

- `phone_focus_mode/systemd/install_pc_phone_automation.sh`
- `phone_focus_mode/systemd/phone-auto-sync.service`
- `phone_focus_mode/systemd/phone-auto-sync.timer`

Responsibilities:

- install user-level automation on the PC
- periodically call the visible wrapper in safe `auto` mode
- serve as a fallback when hotplug or live discovery is imperfect

## Backup storage layout

Backups must be stored outside the Git workspace in a configurable local host
path. This avoids polluting the repository with large APKs, app data, media,
and other binary artifacts that violate the workspace’s normal storage rules.

Recommended structure:

- `../testsAndMisc_binaries/phone_focus_backups/<device-id>/latest/`
- `../testsAndMisc_binaries/phone_focus_backups/<device-id>/history/<timestamp>/`

Only small text manifests or reports may live in-repo when helpful. APKs,
media, databases, and app-data payloads must stay in the external backup root.

Each snapshot should contain the following subdirectories.

### `device_info/`

- device properties
- Android version and build fingerprint
- installed package inventory
- partition and storage information
- serial and connection metadata

### `security_state/`

- generated canonical hosts file
- launcher APK snapshot and pinned activity metadata
- focus-mode logs and status files
- daemon and enforcer health snapshots
- DNS and firewall status outputs

### `apks/`

- selected APK exports for reinstallable apps

### `app_data/`

- configured rooted data pulls for selected packages

### `media/`

- configured user-facing storage such as photos, downloads, and documents

### `monitoring/`

- device-health snapshots over time
- summarized alert reports
- JSON snapshots suitable for later tooling or diffing

---
post_title: "Phone focus recovery design"
author1: "GitHub Copilot"
post_slug: "phone-focus-recovery-design"
microsoft_alias: "copilot"
featured_image: ""
categories:
	- "Documentation"
tags:
	- "android"
	- "adb"
	- "backup"
	- "shell"
ai_note: "AI-assisted design document"
summary: "Design for a rooted-Android recovery, backup, monitoring, and one-command orchestration workflow built on phone_focus_mode."
post_date: "2026-05-01"
---

## Goal

Create a repeatable rooted-Android management workflow that can:

- restore a freshly formatted phone to the previously hardened state
- back up important phone state whenever the phone appears on this PC
- monitor security and device-health drift over time
- expose one highly visible entrypoint at `scripts/run_all/run_phone.sh`

The design must build on the existing `phone_focus_mode/` deployment system
instead of replacing it with a second parallel toolchain.

## Existing foundation

The existing `phone_focus_mode/` implementation already provides the core
security stack:

- `deploy.sh` deploys the focus scripts and companion app over ADB
- `focus_daemon.sh` enforces location-based focus restrictions
- `hosts_enforcer.sh` protects `/system/etc/hosts`
- `dns_enforcer.sh` forces DNS behavior that respects the hosts file
- `launcher_enforcer.sh` keeps the approved launcher installed and pinned
- `magisk_service.sh` restores the protections automatically on boot

The new workflow should reuse these assets rather than re-implement them.

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

## Command modes

The implementation should support explicit subcommands plus a safe default.

### Default mode: `auto`

Invoked by:

```bash
./scripts/run_all/run_phone.sh
```

Flow:

1. discover or select exactly one device
2. verify root and repository prerequisites
3. **check for fresh-format indicators** (absence of focus scripts at expected
   paths, missing daemon PIDs, absent magisk module, empty/missing `STATE_DIR`,
   known app whitelist not installed)
   - **If format detected:** print a clearly formatted warning block naming each
     missing indicator, explain that the phone appears to have been wiped, and
     suggest running `fresh-phone` mode. **Exit immediately. Do nothing else.**
4. collect a quick monitoring snapshot
5. run incremental backup steps
6. inspect the security stack for drift
7. repair minor drift when the repair is low risk
8. print a summary with warnings and any skipped actions

`auto` mode must never perform any restore or re-deployment action. It is
read-and-report only when the phone looks healthy, and detect-and-warn only
when the phone looks wiped.

### `fresh-phone`

Invoked by:

```bash
./scripts/run_all/run_phone.sh fresh-phone
```

Flow:

1. connect to the target phone
2. verify root and backup availability
3. record a pre-change snapshot
4. restore security assets first
5. restore launcher snapshot and home activity
6. restore selected APKs
7. restore selected app data
8. restore configured user files
9. run full verification
10. print manual follow-up steps, if any

If the phone is not yet in the minimum expected state, the workflow must stop
with a precise checklist rather than performing a partial restore.

### `backup`

Flow:

1. detect or connect device
2. create timestamped snapshot directory
3. collect metadata, APKs, app data, media, and security state
4. update the `latest/` snapshot pointer or mirror
5. prune history according to retention policy

### `monitor`

Flow:

1. detect or connect device
2. collect health and security state
3. compare against thresholds and prior snapshots
4. emit human-readable and machine-readable reports
5. return nonzero exit status on severe drift

### `doctor`

Flow:

1. run the monitoring checks
2. attempt low-risk repairs
3. restart missing daemons or re-push missing security assets if needed
4. stop before broad data restore actions
5. print repaired vs unresolved issues clearly

## Repair policy by mode

The implementation must use an explicit repair allowlist instead of treating
“minor drift” as an open-ended concept.

### Repairs allowed in `auto`

- restart managed daemons when scripts and state already exist
- restart the companion status app when it is already part of the setup
- reassert hosts, DNS, or launcher enforcement when the required backing files
  already exist locally and on-device
- re-run deployment of the security stack when the drift is clearly limited to
  managed `phone_focus_mode` assets

### Repairs forbidden in `auto`

- broad APK restore
- app-data restore
- media restore
- any action that changes user data outside the managed security stack
- any destructive cleanup of backup history

### Repairs allowed in `doctor`

- everything allowed in `auto`
- reinstall the companion app
- restore launcher snapshot and HOME activity when launcher backup metadata is
  present
- re-push missing managed security assets from the local project state

### Repairs forbidden in `doctor`

- broad app-data restore
- media restore
- destructive reset of on-device state outside the managed security stack

### Actions allowed only in `fresh-phone`

- APK reinstall from backup
- selected app-data restore according to manifest policy
- configured media and user-file restore

Any action outside these allowlists must require explicit future design or
manual operator intent.

## Device detection and connection policy

The workflow must support both USB and wireless ADB.

Selection order:

1. use an explicitly supplied serial if present
2. use the only already-connected device if there is exactly one
3. use a saved wireless endpoint when available
4. try controlled wireless discovery fallback
5. fail with a clear message when multiple candidate devices exist

The workflow must avoid acting on the wrong device silently.

### Trusted identity requirements

The implementation should persist and verify a trusted identity record for the
managed phone, including:

- preferred ADB serial or wireless endpoint
- device model
- Android build fingerprint
- a stable property such as serial or hardware identifier when available

The script must refuse to proceed automatically when:

- more than one viable device is connected
- the connected device identity no longer matches the trusted record
- both USB and wireless sessions point to ambiguous or conflicting targets

### First-run and post-format prerequisites

`fresh-phone` cannot assume that all prerequisites already exist. Before any
restore work, the script must verify:

- USB debugging is authorized or wireless debugging is paired
- ADB can reach the device reliably
- Magisk and root are available
- root shell commands succeed in the expected mount namespace

If any prerequisite is missing, the command must stop and print the manual
steps required to continue, such as USB authorization, Magisk installation, or
first-time wireless pairing.

## Architecture boundary with existing deployment code

The implementation must not duplicate the core deployment logic already present
in `phone_focus_mode/deploy.sh`.

Rules:

- `deploy.sh` remains the deployment primitive for pushing security assets and
  bringing up the phone hardening stack
- `run_phone.sh` may wrap or call `deploy.sh`, but must not reimplement its
  file-push, daemon-start, or root-verification logic in parallel
- shared ADB and device-selection helpers may be extracted into common library
  functions when that reduces duplication across both scripts

### Concrete integration path

The implementation plan should follow this sequence:

1. extract transport-agnostic ADB targeting helpers into
   `phone_focus_mode/lib/adb_common.sh`
2. refactor `deploy.sh` so it can operate on a resolved target serial or
   selected device abstraction rather than assuming a raw phone IP only
3. make `phone_focus_mode/run_phone.sh` the orchestration layer that performs
   selection, backup, monitoring, and then delegates deployment work to
   `deploy.sh`

This path preserves the proven deployment behavior while making it compatible
with USB and wireless device selection.

This keeps the new orchestration layer from drifting away from the proven
deployment flow.

## Monitoring scope

Monitoring should cover all user-requested areas.

### Battery wear and thermal state

- battery level
- charge status
- health and temperature if exposed
- evidence of abnormal thermal throttling or overheating

### Storage pressure and filesystem issues

- free space on major storage locations
- install/update failures caused by storage exhaustion
- signs of partition or package-management problems

### Performance and resource drift

- memory pressure indicators
- unusually heavy processes
- persistent crash or restart loops in the managed daemons

### Security drift

- focus daemon running or not
- hosts enforcer running or not
- DNS enforcer running or not
- launcher enforcer running or not
- companion app installed or missing

### Network and DNS bypass drift

- Private DNS re-enabled
- expected firewall chain missing
- hosts target hash or mount mismatch
- launcher default changed away from the protected launcher

### Boot persistence drift

- Magisk `service.d` script missing or no longer executable
- expected on-device files missing from `focus_mode`
- companion app missing when it is required for status visibility

## Monitoring report contract

Every monitoring run should produce two outputs:

- a concise human-readable summary
- a machine-readable report file suitable for later diffing and automation

Recommended report path pattern:

- `<backup-root>/<device-id>/monitoring/<timestamp>.json`
- `<backup-root>/<device-id>/monitoring/latest.json`

Recommended trusted-device record path:

- `${XDG_STATE_HOME:-$HOME/.local/state}/phone_focus_mode/trusted_device.sh`

Recommended runtime-automation state paths:

- `${XDG_STATE_HOME:-$HOME/.local/state}/phone_focus_mode/locks/`
- `${XDG_STATE_HOME:-$HOME/.local/state}/phone_focus_mode/last_run/`

Daily automation must not dirty the repository working tree merely by being
used. Trusted-device metadata, lock files, cooldown markers, and last-run
timestamps should therefore live in machine-local state outside the repo.

Recommended latest-backup pointer behavior:

- `latest/` should be a symlink to the newest history snapshot when the host
  filesystem supports symlinks
- otherwise `latest/` may be refreshed as a copied mirror of the newest
  snapshot

The machine-readable report should distinguish at least these severities:

- `ok`
- `warn`
- `error`
- `fatal`

Each reported check should record:

- check name
- status/severity
- evidence source
- short message
- whether the issue is repairable automatically

Important checks should verify more than just PID existence. For example:

- hosts protection should confirm both the canonical hash and the active
  target mount/content state
- DNS protection should confirm Private DNS settings and firewall chain
  presence
- launcher protection should confirm installation, stored snapshot metadata,
  and current default HOME activity
- boot persistence should confirm the expected Magisk boot script is present

`monitor` should exit nonzero on severe drift. `doctor` should use the same
report format while additionally recording what was repaired.

For the initial implementation, “severe drift” should mean any of:

- target device identity mismatch
- no root access when root-dependent checks are required
- hosts enforcement missing or failing integrity checks
- DNS enforcement missing when it was previously configured
- launcher protection missing when launcher protection was previously
  configured
- missing boot persistence for the managed stack

History retention and pruning policy should be locked down in the
implementation plan, but the initial default should favor safety over
aggressive deletion.

## Restore priority order

When the phone is freshly formatted or in a degraded state, restore in this
priority order:

1. connection and root verification
2. security scripts and boot persistence
3. canonical hosts and DNS protections
4. launcher enforcement and companion app
5. APK reinstall support
6. selected app data
7. media and user files

## Backup and restore policy classification

Each manifest entry should specify how it may be restored.

Suggested fields:

- `name`
- `kind` (`apk`, `app_data`, `media`, `security_state`)
- `backup_paths`
- `restore_policy` (`safe_restore`, `manual_only`, `backup_only`)
- `requires_root`
- `requires_version_match`
- `integrity_check`
- `contains_secrets`

The implementation must never silently restore unsupported or risky payloads.
When restore safety is uncertain, it should back up the data and report it as
manual-only.

### Conservative v1 restore policy

For the initial implementation, app-data restore should default to the most
conservative stance:

- no app-data entries should ship as `safe_restore` by default
- app-data items should default to `manual_only` unless a later design change
  explicitly promotes a named package after validation
- APK restore, security-state restore, and configured media/file restore may
  proceed according to their own manifest policies without implying that
  private app-data restore is equally safe

This keeps v1 focused on reliable security recovery and host-side backups while
avoiding premature promises about rooted Android app-data portability.

### Canonical manifest examples

The manifest should include entries with a concrete shell-native shape. For
example:

```bash
APK_ITEMS=(
	"com.qqlabs.minimalistlauncher|safe_restore|yes|yes"
)

APP_DATA_ITEMS=(
	"com.beemdevelopment.aegis|/data/data/com.beemdevelopment.aegis|manual_only|yes|yes"
)

MEDIA_ITEMS=(
	"photos|/sdcard/DCIM|safe_restore|no|no"
)
```

Where each pipe-delimited record maps to:

- name or package
- source path
- restore policy
- requires root
- requires integrity check

The implementation may wrap these records with helper functions, but should
keep the manifest format simple enough to read and edit without custom tools.

This ordering ensures the phone becomes safe again before broader recovery
work continues.

## Documentation and discoverability requirements

The final implementation must make the workflow obvious in at least two
places.

### README requirements

`phone_focus_mode/README.md` should document:

- the visible wrapper location
- the three core user flows:
  - normal day
  - after format
  - if something feels wrong
- examples for `auto`, `fresh-phone`, `doctor`, `backup`, and `monitor`
- backup scope and monitoring expectations

### Script help-text requirements

Both `scripts/run_all/run_phone.sh` and `phone_focus_mode/run_phone.sh`
should expose help text that includes the memorable usage guidance:

- run the wrapper with no arguments for everyday backup and minor repair
- run `fresh-phone` after a format
- run `doctor` when the phone seems unhealthy or protections drifted

This is not just documentation; it is part of the usability contract.

## Automation safety rules

Because the phone may appear repeatedly over USB or Wi-Fi, automation must be
conservative.

Required safeguards:

- single-instance lock to prevent overlapping runs
- cooldown window so repeated reconnects do not trigger backup storms
- clear separation between lightweight `auto` mode and heavier full-backup
  behavior
- retry and backoff rules for transient ADB failures
- no automatic `fresh-phone` restore without explicit user intent

## Testing and verification expectations

The implementation phase should follow strict shell hygiene and repository
quality rules.

- use `set -euo pipefail`
- prefer reusable functions over repeated ADB snippets
- validate parameters and environment clearly
- keep destructive operations explicit and well-logged
- add tests where practical for shell logic or parser behavior
- run `pre-commit run --files <changed-files>` before claiming completion

Verification must include:

- shell syntax validation
- targeted script execution in safe modes
- README/help-text verification against the approved user flows
- evidence that backups and monitoring output are actually produced

## Constraints and non-goals

The design deliberately does not promise impossible guarantees.

- It cannot make a rooted phone impossible to tamper with locally.
- It cannot safely restore every app’s private data without app-specific risk.
- It should prefer explicit warnings over pretending unsupported restores are
  safe.

The goal is a robust, repeatable, operator-friendly recovery and monitoring
system, not an infallible anti-root fortress.

## Open implementation notes

- Reuse code patterns already present in `linux_configuration/scripts/utils/`
  and `python_pkg/screen_locker/_phone_verification.py` where they help with
  ADB detection and wireless reconnection.
- Keep the wrapper stable even if the internal phone implementation evolves.
- Preserve the existing `deploy.sh` value rather than rewriting it from
  scratch.
- Make backup scope declarative so expanding or narrowing coverage does not
  require editing core shell control flow.

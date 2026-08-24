# Command modes, repair policy and device detection

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

# Monitoring scope and the report contract

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

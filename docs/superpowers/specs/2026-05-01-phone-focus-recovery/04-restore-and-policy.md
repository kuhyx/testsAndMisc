# Restore priority, backup policy and documentation requirements

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

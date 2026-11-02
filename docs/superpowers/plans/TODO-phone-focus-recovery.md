# Live-verify phone recovery workflow (Chunk 8 of the original plan)

## what
Chunks 1-7 of the plan are built and now live in `~/src/phone-focus-mode`
(`run_phone.sh`, `lib/{adb_common,monitor,backup,restore}.sh`,
`backup_manifest.sh`, `systemd/phone-auto-sync.*`, README). The visible
wrapper moved: the entry point is `~/src/phone-focus-mode/run_phone.sh`. What
is left is the one-off run against the real, rooted phone.

## done
With the phone connected over ADB, from `~/src/phone-focus-mode`:
`./run_phone.sh --help`, `monitor`, `backup` and `auto` all exit 0, `backup`
writes under `~/phone_backups/`, and a temporary extra entry in
`FORMAT_INDICATORS` (`backup_manifest.sh`, reverted afterwards) makes `auto`
print the formatted-phone warning and stop without doing anything else.

## verify
Needs kuhy: phone attached (`adb devices` lists it, none was attached on
2026-11-02). Library tests already pass: `lib/tests/test_adb_common.sh`
(10 passed) and `lib/tests/test_monitor.sh` (82 passed).

## read first
- `~/src/phone-focus-mode/README.md`
- `~/src/phone-focus-mode/CLAUDE.md`

REMOVE ME AFTER FINISH

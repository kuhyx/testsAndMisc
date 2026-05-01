# Phone Focus Recovery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-command phone management workflow (`scripts/run_all/run_phone.sh`) that detects formatting, takes incremental backups, monitors security drift, and fully restores a freshly formatted rooted Android phone to its hardened state.

**Architecture:** A thin visible wrapper (`scripts/run_all/run_phone.sh`) forwards to the project-local orchestrator (`phone_focus_mode/run_phone.sh`), which delegates to focused library modules in `phone_focus_mode/lib/`. The existing `deploy.sh` remains the deployment primitive; the new code wraps it rather than replacing it.

**Tech Stack:** Bash 5 (`set -euo pipefail`), ADB, Magisk/root, ShellCheck, pre-commit.

---

## Chunk 1: Foundation — `lib/adb_common.sh`

### Files

- Create: `phone_focus_mode/lib/adb_common.sh`
- Create: `phone_focus_mode/lib/tests/test_adb_common.sh`

### Background

`adb_common.sh` is the lowest layer. Every other module sources it. It handles:

- locating exactly one target device (USB or wireless)
- verifying root access
- providing a single `adb_root_shell` function used everywhere instead of duplicating `su --mount-master -c` calls
- saving and loading the trusted-device identity record

The trusted-device record lives at:

```
${XDG_STATE_HOME:-$HOME/.local/state}/phone_focus_mode/trusted_device.sh
```

It is a shell-native sourceable file (no JSON, no jq).

State and lock directories:

```
${XDG_STATE_HOME:-$HOME/.local/state}/phone_focus_mode/locks/
${XDG_STATE_HOME:-$HOME/.local/state}/phone_focus_mode/last_run/
```

---

- [ ] **Step 1.1: Create the library file skeleton**

Create `phone_focus_mode/lib/adb_common.sh`:

```bash
#!/usr/bin/env bash
# lib/adb_common.sh — ADB device selection, identity, and root helpers.
# Source this file; do not execute directly.
set -euo pipefail

# ---------------------------------------------------------------------------
# State paths
# ---------------------------------------------------------------------------
_PHONE_STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/phone_focus_mode"
TRUSTED_DEVICE_FILE="${_PHONE_STATE_DIR}/trusted_device.sh"
LOCK_DIR="${_PHONE_STATE_DIR}/locks"
LAST_RUN_DIR="${_PHONE_STATE_DIR}/last_run"

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
_info()  { printf '\033[0;34m[INFO]\033[0m  %s\n' "$*" >&2; }
_warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*" >&2; }
_error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }
_fatal() { printf '\033[0;31m[FATAL]\033[0m %s\n' "$*" >&2; exit 1; }

_box() {
    local title="$1"; shift
    printf '\n\033[1;33m╔══════════════════════════════════════════╗\033[0m\n' >&2
    printf '\033[1;33m║  %-42s║\033[0m\n' "${title}" >&2
    printf '\033[1;33m╚══════════════════════════════════════════╝\033[0m\n' >&2
    for line in "$@"; do
        printf '  %s\n' "${line}" >&2
    done
}

# ---------------------------------------------------------------------------
# adb_list_serials — print one serial per line for all connected devices
# ---------------------------------------------------------------------------
adb_list_serials() {
    adb devices 2>/dev/null \
        | awk 'NR>1 && $2~/^(device|offline|unauthorized)$/ { print $1 }'
}

# ---------------------------------------------------------------------------
# adb_select_device [serial]
# Sets and exports ADB_SERIAL to the resolved device serial.
# Fails when no device, multiple devices and no serial supplied, or when the
# supplied serial does not appear in the connected device list.
# ---------------------------------------------------------------------------
adb_select_device() {
    local requested="${1:-${ADB_SERIAL:-}}"
    local -a serials
    mapfile -t serials < <(adb_list_serials)

    if [[ ${#serials[@]} -eq 0 ]]; then
        _fatal "No ADB device found. Connect via USB or pair wireless ADB first."
    fi

    if [[ -n "${requested}" ]]; then
        local found=0
        for s in "${serials[@]}"; do
            [[ "${s}" == "${requested}" ]] && found=1 && break
        done
        [[ "${found}" -eq 1 ]] \
            || _fatal "Requested device '${requested}' not found. Connected: ${serials[*]}"
        export ADB_SERIAL="${requested}"
        return 0
    fi

    if [[ ${#serials[@]} -eq 1 ]]; then
        export ADB_SERIAL="${serials[0]}"
        _info "Auto-selected device: ${ADB_SERIAL}"
        return 0
    fi

    # Multiple devices — try saved trusted device
    if [[ -f "${TRUSTED_DEVICE_FILE}" ]]; then
        local saved_serial=""
        # shellcheck source=/dev/null
        source "${TRUSTED_DEVICE_FILE}"
        saved_serial="${TRUSTED_SERIAL:-}"
        if [[ -n "${saved_serial}" ]]; then
            for s in "${serials[@]}"; do
                if [[ "${s}" == "${saved_serial}" ]]; then
                    export ADB_SERIAL="${saved_serial}"
                    _info "Selected saved trusted device: ${ADB_SERIAL}"
                    return 0
                fi
            done
        fi
    fi

    _fatal "Multiple ADB devices found (${serials[*]}) and no target specified. Use --serial or set ADB_SERIAL."
}

# ---------------------------------------------------------------------------
# adb_cmd — run an adb command targeting the selected device
# ---------------------------------------------------------------------------
adb_cmd() {
    adb -s "${ADB_SERIAL:?adb_select_device must be called first}" "$@"
}

# ---------------------------------------------------------------------------
# adb_verify_root — confirm su --mount-master -c works on the device
# ---------------------------------------------------------------------------
adb_verify_root() {
    local result
    result=$(adb_cmd shell su --mount-master -c "echo ok" 2>/dev/null || true)
    [[ "${result}" == "ok" ]] \
        || _fatal "Root check failed on ${ADB_SERIAL}. Ensure Magisk is installed and ADB root is authorized."
    _info "Root verified on ${ADB_SERIAL}"
}

# ---------------------------------------------------------------------------
# adb_root_shell CMD — run CMD on device under su --mount-master
# ---------------------------------------------------------------------------
adb_root_shell() {
    adb_cmd shell su --mount-master -c "$*"
}

# ---------------------------------------------------------------------------
# _sanitize_device_string — strip chars that would be dangerous in a sourced .sh file
# ---------------------------------------------------------------------------
_sanitize_device_string() {
    # Allow only printable ASCII: alphanumeric, space, dash, dot, colon, slash, underscore.
    # Strips quotes, $, backtick, semicolon, newline, and anything else.
    printf '%s' "$1" | tr -cd 'A-Za-z0-9 ._:/\-'
}

# ---------------------------------------------------------------------------
# adb_collect_identity — populate DEVICE_MODEL, DEVICE_FINGERPRINT, DEVICE_SERIAL
# ---------------------------------------------------------------------------
adb_collect_identity() {
    local raw_model raw_fp
    raw_model=$(adb_cmd shell getprop ro.product.model 2>/dev/null | tr -d '\r')
    raw_fp=$(adb_cmd shell getprop ro.build.fingerprint 2>/dev/null | tr -d '\r')
    DEVICE_MODEL=$(_sanitize_device_string "${raw_model}")
    DEVICE_FINGERPRINT=$(_sanitize_device_string "${raw_fp}")
    DEVICE_SERIAL=$(_sanitize_device_string "${ADB_SERIAL}")
    export DEVICE_MODEL DEVICE_FINGERPRINT DEVICE_SERIAL
}

# ---------------------------------------------------------------------------
# adb_save_trusted_device — write trusted_device.sh
# ---------------------------------------------------------------------------
adb_save_trusted_device() {
    adb_collect_identity
    mkdir -p "${_PHONE_STATE_DIR}"
    # Values have been sanitized by _sanitize_device_string.
    # printf %q provides an extra layer of quoting safety.
    {
        printf '# Auto-generated trusted device record — do not edit manually.\n'
        printf 'TRUSTED_SERIAL=%q\n'      "${DEVICE_SERIAL}"
        printf 'TRUSTED_MODEL=%q\n'       "${DEVICE_MODEL}"
        printf 'TRUSTED_FINGERPRINT=%q\n' "${DEVICE_FINGERPRINT}"
    } > "${TRUSTED_DEVICE_FILE}"
    chmod 600 "${TRUSTED_DEVICE_FILE}"
    _info "Saved trusted device record: model='${DEVICE_MODEL}' serial='${DEVICE_SERIAL}'"
}

# ---------------------------------------------------------------------------
# adb_verify_trusted_identity — compare current device to saved record
# Exits non-zero with an error message if identity does not match.
# ---------------------------------------------------------------------------
adb_verify_trusted_identity() {
    if [[ ! -f "${TRUSTED_DEVICE_FILE}" ]]; then
        _warn "No trusted device record found. Run 'fresh-phone' to enroll this device."
        return 0  # First run — allow with a warning, not a hard failure
    fi
    local saved_serial="" saved_fp=""
    # shellcheck source=/dev/null
    source "${TRUSTED_DEVICE_FILE}"
    saved_serial="${TRUSTED_SERIAL:-}"
    saved_fp="${TRUSTED_FINGERPRINT:-}"

    adb_collect_identity

    if [[ -n "${saved_serial}" && "${DEVICE_SERIAL}" != "${saved_serial}" ]]; then
        _fatal "Device identity mismatch: expected serial '${saved_serial}', got '${DEVICE_SERIAL}'. Refusing to proceed automatically."
    fi
    if [[ -n "${saved_fp}" && "${DEVICE_FINGERPRINT}" != "${saved_fp}" ]]; then
        _warn "Build fingerprint changed: expected '${saved_fp}', got '${DEVICE_FINGERPRINT}'. Verify the device is the correct one before continuing."
    fi
    _info "Device identity verified: ${DEVICE_SERIAL} (${DEVICE_MODEL})"
}

# ---------------------------------------------------------------------------
# adb_acquire_lock — single-instance lock to prevent overlapping runs
# ---------------------------------------------------------------------------
LOCK_FILE=""
adb_acquire_lock() {
    mkdir -p "${LOCK_DIR}"
    LOCK_FILE="${LOCK_DIR}/run_phone.lock"
    if [[ -e "${LOCK_FILE}" ]]; then
        local old_pid
        old_pid=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
        if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
            _fatal "Another run_phone.sh instance is already running (PID ${old_pid}). Aborting."
        else
            _warn "Stale lock file found (PID ${old_pid} no longer running). Removing."
            rm -f "${LOCK_FILE}"
        fi
    fi
    echo $$ > "${LOCK_FILE}"
    trap '_adb_release_lock' EXIT INT TERM
    _info "Acquired run lock (PID $$)"
}

_adb_release_lock() {
    [[ -n "${LOCK_FILE}" && -f "${LOCK_FILE}" ]] && rm -f "${LOCK_FILE}"
}

# ---------------------------------------------------------------------------
# adb_check_cooldown COOLDOWN_SECONDS MARKER_NAME
# Exits 0 (ok to proceed) or 1 (too soon, caller should skip).
# ---------------------------------------------------------------------------
adb_check_cooldown() {
    local cooldown_secs="${1:-300}"
    local marker_name="${2:-default}"
    local marker="${LAST_RUN_DIR}/${marker_name}"
    mkdir -p "${LAST_RUN_DIR}"
    if [[ -f "${marker}" ]]; then
        local last_run now elapsed
        last_run=$(cat "${marker}")
        now=$(date +%s)
        elapsed=$(( now - last_run ))
        if (( elapsed < cooldown_secs )); then
            _info "Cooldown active: last run ${elapsed}s ago, cooldown is ${cooldown_secs}s. Skipping."
            return 1
        fi
    fi
    return 0
}

adb_mark_last_run() {
    local marker_name="${1:-default}"
    mkdir -p "${LAST_RUN_DIR}"
    date +%s > "${LAST_RUN_DIR}/${marker_name}"
}
```

- [ ] **Step 1.2: Create the test file**

Create `phone_focus_mode/lib/tests/test_adb_common.sh`:

```bash
#!/usr/bin/env bash
# Unit tests for adb_common.sh helper functions (no real device needed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../adb_common.sh"

PASS=0
FAIL=0
_t_pass() { PASS=$(( PASS + 1 )); printf '  OK: %s\n' "$1"; }
_t_fail() { FAIL=$(( FAIL + 1 )); printf '  FAIL: %s\n' "$1"; }

# --- test _box does not crash ---
_box "Test title" "line 1" "line 2" 2>/dev/null
_t_pass "_box output without crash"

# --- test adb_check_cooldown with zero cooldown always proceeds ---
LAST_RUN_DIR="$(mktemp -d)"
trap 'rm -rf "${LAST_RUN_DIR}"' EXIT
if adb_check_cooldown 0 "test_marker"; then
    _t_pass "adb_check_cooldown 0 returns 0 (proceed)"
else
    _t_fail "adb_check_cooldown 0 should return 0"
fi

# --- test cooldown blocks when marker is fresh ---
echo "$(date +%s)" > "${LAST_RUN_DIR}/fresh_marker"
if adb_check_cooldown 9999 "fresh_marker"; then
    _t_fail "adb_check_cooldown 9999 should return 1 (blocked)"
else
    _t_pass "adb_check_cooldown 9999 returns 1 (blocked) with fresh marker"
fi

# --- test adb_mark_last_run creates marker ---
adb_mark_last_run "run_test"
[[ -f "${LAST_RUN_DIR}/run_test" ]] \
    && _t_pass "adb_mark_last_run creates marker file" \
    || _t_fail "adb_mark_last_run did not create marker"

printf '\nResults: %d passed, %d failed\n' "${PASS}" "${FAIL}"
[[ "${FAIL}" -eq 0 ]]
```

- [ ] **Step 1.3: Run the test to verify it passes**

```bash
cd /home/kuhy/testsAndMisc
bash phone_focus_mode/lib/tests/test_adb_common.sh
```

Expected: all tests pass, `Results: N passed, 0 failed`.

- [ ] **Step 1.4: Run ShellCheck**

```bash
shellcheck --severity=warning phone_focus_mode/lib/adb_common.sh
shellcheck --severity=warning phone_focus_mode/lib/tests/test_adb_common.sh
```

Expected: no warnings or errors.

- [ ] **Step 1.5: Commit**

```bash
git add phone_focus_mode/lib/adb_common.sh phone_focus_mode/lib/tests/test_adb_common.sh
git commit -m "feat(phone): add lib/adb_common.sh — device selection, identity, root, locking"
```

---

## Chunk 2: Declarative config — `backup_manifest.sh`

### Files

- Create: `phone_focus_mode/backup_manifest.sh`

### Background

`backup_manifest.sh` is the user-editable scope definition. It declares:

- which APKs to snapshot
- which app-data locations to capture (all `manual_only` by default for v1)
- which media directories to sync
- health check thresholds

All records use **bash arrays** (`APK_ITEMS=(...)`) where each element is a
pipe-delimited string. This requires bash (not POSIX sh) — all scripts target
bash 5 via `#!/usr/bin/env bash`. Consuming scripts iterate with
`for entry in "${APK_ITEMS[@]}"` and extract fields with `cut -d'|' -f<N>`.

Default backup root (override via `PHONE_BACKUP_ROOT` env var):

```
~/phone_backups
```

Full path per device: `${PHONE_BACKUP_ROOT}/<device-id>/`

---

- [ ] **Step 2.1: Create `backup_manifest.sh`**

Create `phone_focus_mode/backup_manifest.sh`:

```bash
#!/usr/bin/env bash
# backup_manifest.sh — Declarative backup and restore scope definition.
# Source this file; do not execute directly.
# Fields: name|source_path|restore_policy|requires_root|integrity_check
#
# restore_policy values:
#   safe_restore   — may be restored automatically
#   manual_only    — backed up but never restored without operator action
#   backup_only    — backed up but restore is not yet implemented
#
# Format-detection thresholds (edit as needed):
FORMAT_DETECTION_MIN_MISSING=2   # ≥ this many missing indicators → alert

# ---------------------------------------------------------------------------
# Backup root (override with PHONE_BACKUP_ROOT env var)
# ---------------------------------------------------------------------------
PHONE_BACKUP_ROOT="${PHONE_BACKUP_ROOT:-${HOME}/phone_backups}"

# ---------------------------------------------------------------------------
# APKs to snapshot and reinstall
# Fields: package_id|restore_policy|requires_root|integrity_check
# ---------------------------------------------------------------------------
APK_ITEMS=(
    "com.qqlabs.minimalistlauncher|safe_restore|no|yes"
    "com.kuhy.focusstatus|safe_restore|no|yes"
)

# ---------------------------------------------------------------------------
# App data (v1: all manual_only — see spec §Conservative v1 restore policy)
# Fields: package_id|data_path|restore_policy|requires_root|integrity_check
# ---------------------------------------------------------------------------
APP_DATA_ITEMS=(
    "com.beemdevelopment.aegis|/data/data/com.beemdevelopment.aegis|manual_only|yes|yes"
)

# ---------------------------------------------------------------------------
# Media and user files
# Fields: name|on_device_path|restore_policy|requires_root|integrity_check
# ---------------------------------------------------------------------------
MEDIA_ITEMS=(
    "photos|/sdcard/DCIM|safe_restore|no|no"
    "downloads|/sdcard/Download|safe_restore|no|no"
    "documents|/sdcard/Documents|safe_restore|no|no"
)

# ---------------------------------------------------------------------------
# Security state files to capture (relative to known on-device paths)
# ---------------------------------------------------------------------------
SECURITY_STATE_FILES=(
    "/data/adb/service.d/99-focus-mode.sh"
    "/data/adb/focus_mode/hosts.canonical"
    "/data/local/tmp/focus_mode/focus_state"
)

# ---------------------------------------------------------------------------
# Format-detection indicators
# Each entry: description|adb_test_command
# adb_test_command should exit 0 when the indicator IS present (not wiped).
# ---------------------------------------------------------------------------
FORMAT_INDICATORS=(
    "Magisk boot script|test -f /data/adb/service.d/99-focus-mode.sh"
    "Focus mode data dir|test -d /data/adb/focus_mode"
    "Focus mode state dir|test -d /data/local/tmp/focus_mode"
    "Minimalist launcher installed|pm list packages -e com.qqlabs.minimalistlauncher | grep -q com.qqlabs.minimalistlauncher"
    "Focus companion app installed|pm list packages -e com.kuhy.focusstatus | grep -q com.kuhy.focusstatus"
)

# ---------------------------------------------------------------------------
# Monitoring thresholds
# ---------------------------------------------------------------------------
BATTERY_WARN_BELOW=20          # % — warn when battery below this level
STORAGE_WARN_BELOW_MB=500      # MB free — warn when main storage below this
COOLDOWN_AUTO_SECS=300         # 5 min between auto runs (prevent backup storms)
HISTORY_KEEP_DAYS=30           # prune history snapshots older than this
```

- [ ] **Step 2.2: Run ShellCheck**

```bash
shellcheck --severity=warning phone_focus_mode/backup_manifest.sh
```

Expected: no warnings.

- [ ] **Step 2.3: Commit**

```bash
git add phone_focus_mode/backup_manifest.sh
git commit -m "feat(phone): add backup_manifest.sh — declarative APK/data/media/format-detection config"
```

---

## Chunk 3: Monitoring library — `lib/monitor.sh`

### Files

- Create: `phone_focus_mode/lib/monitor.sh`
- Create: `phone_focus_mode/lib/tests/test_monitor.sh`

### Background

`monitor.sh` provides:

- `monitor_collect_snapshot SNAPSHOT_DIR` — runs all checks, writes JSON report
- `monitor_check_format_indicators` — checks FORMAT_INDICATORS from manifest, returns missing count
- `monitor_print_summary SNAPSHOT_DIR` — human-readable summary from JSON report
- `monitor_severity_exit SNAPSHOT_DIR` — exit 1 if any `fatal` or `error` severity items exist

The JSON report is written to `${SNAPSHOT_DIR}/report.json`.
The report uses severity: `ok`, `warn`, `error`, `fatal`.

Each check record:

```json
{
  "check": "name",
  "status": "ok|warn|error|fatal",
  "source": "command",
  "message": "...",
  "repairable": true
}
```

---

- [ ] **Step 3.1: Create `lib/monitor.sh`**

Create `phone_focus_mode/lib/monitor.sh`:

```bash
#!/usr/bin/env bash
# lib/monitor.sh — Security and health monitoring for the managed phone.
# Requires: adb_common.sh sourced, ADB_SERIAL set, backup_manifest.sh sourced.
set -euo pipefail

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_mon_check() {
    # _mon_check CHECK_NAME STATUS SOURCE MESSAGE REPAIRABLE
    local name="$1" status="$2" source="$3" message="$4" repairable="${5:-false}"
    printf '{"check":"%s","status":"%s","source":"%s","message":"%s","repairable":%s}\n' \
        "${name}" "${status}" "${source}" "${message}" "${repairable}"
}

_safe_adb_root() {
    # Run adb root shell command; return empty string on failure rather than exit.
    adb_root_shell "$@" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# monitor_check_format_indicators
# Prints each missing indicator name to stdout (one per line).
# Returns the count of missing indicators via exit code 0 always;
# caller should count output lines.
# ---------------------------------------------------------------------------
monitor_check_format_indicators() {
    local indicator desc cmd result
    for indicator in "${FORMAT_INDICATORS[@]}"; do
        desc="${indicator%%|*}"
        cmd="${indicator#*|}"
        result=$(_safe_adb_root "${cmd}" 2>/dev/null || echo "MISSING")
        # Command exits non-zero → indicator is absent
        if ! adb_root_shell "${cmd}" >/dev/null 2>&1; then
            printf '%s\n' "${desc}"
        fi
    done
}

# ---------------------------------------------------------------------------
# monitor_is_formatted
# Returns 0 if phone appears freshly formatted (≥ FORMAT_DETECTION_MIN_MISSING
# indicators missing), 1 otherwise.
# ---------------------------------------------------------------------------
monitor_is_formatted() {
    local -a missing
    mapfile -t missing < <(monitor_check_format_indicators)
    local count="${#missing[@]}"
    _info "Format-detection: ${count}/${#FORMAT_INDICATORS[@]} indicators missing (threshold: ${FORMAT_DETECTION_MIN_MISSING})"
    (( count >= FORMAT_DETECTION_MIN_MISSING ))
}

# ---------------------------------------------------------------------------
# monitor_print_format_warning MISSING_ARRAY
# ---------------------------------------------------------------------------
monitor_print_format_warning() {
    local -a missing=("$@")
    _box "PHONE APPEARS TO HAVE BEEN WIPED" \
        "" \
        "The following expected components were NOT found:" \
        "${missing[@]/#/  ✗ }" \
        "" \
        "This strongly suggests the phone was factory-reset or formatted." \
        "" \
        "Next step: run the full recovery workflow:" \
        "  ./scripts/run_all/run_phone.sh fresh-phone" \
        "" \
        "Do NOT run 'auto' mode — it will not restore anything." >&2
}

# ---------------------------------------------------------------------------
# _check_battery OUTFILE
# ---------------------------------------------------------------------------
_check_battery() {
    local outfile="$1"
    local level health temp status
    level=$(_safe_adb_root "dumpsys battery | grep level | awk '{print \$2}'" | tr -d '\r')
    health=$(_safe_adb_root "dumpsys battery | grep health | head -1 | awk '{print \$2}'" | tr -d '\r')
    temp=$(_safe_adb_root "dumpsys battery | grep temperature | awk '{print \$2}'" | tr -d '\r')
    status=$(_safe_adb_root "dumpsys battery | grep status | head -1 | awk '{print \$2}'" | tr -d '\r')

    local sev="ok" msg="Battery level ${level}%, health ${health}, temp ${temp}"
    if [[ -n "${level}" ]] && (( level < BATTERY_WARN_BELOW )); then
        sev="warn"
        msg="Battery low: ${level}% (threshold ${BATTERY_WARN_BELOW}%)"
    fi
    _mon_check "battery" "${sev}" "dumpsys battery" "${msg}" "false" >> "${outfile}"
}

# ---------------------------------------------------------------------------
# _check_storage OUTFILE
# ---------------------------------------------------------------------------
_check_storage() {
    local outfile="$1"
    local free_kb free_mb
    free_kb=$(_safe_adb_root "df /sdcard | awk 'NR==2{print \$4}'" | tr -d '\r')
    free_mb=$(( ${free_kb:-0} / 1024 ))

    local sev="ok" msg="Free storage: ${free_mb} MB"
    if (( free_mb < STORAGE_WARN_BELOW_MB )); then
        sev="warn"
        msg="Low storage: ${free_mb} MB free (threshold ${STORAGE_WARN_BELOW_MB} MB)"
    fi
    _mon_check "storage" "${sev}" "df /sdcard" "${msg}" "false" >> "${outfile}"
}

# ---------------------------------------------------------------------------
# _check_daemon NAME PID_CMD OUTFILE
# ---------------------------------------------------------------------------
_check_daemon() {
    local name="$1" pid_cmd="$2" outfile="$3"
    local pid
    pid=$(_safe_adb_root "${pid_cmd}" | tr -d '\r ' || true)
    if [[ -n "${pid}" && "${pid}" =~ ^[0-9]+$ ]]; then
        _mon_check "${name}" "ok" "${pid_cmd}" "${name} running (PID ${pid})" "false" >> "${outfile}"
    else
        _mon_check "${name}" "error" "${pid_cmd}" "${name} is NOT running" "true" >> "${outfile}"
    fi
}

# ---------------------------------------------------------------------------
# _check_hosts_integrity OUTFILE
# ---------------------------------------------------------------------------
_check_hosts_integrity() {
    local outfile="$1"
    local canonical="/data/adb/focus_mode/hosts.canonical"
    local active="/system/etc/hosts"

    if ! adb_root_shell "test -f ${canonical}" >/dev/null 2>&1; then
        _mon_check "hosts_canonical" "fatal" "test -f ${canonical}" \
            "Canonical hosts file missing at ${canonical}" "true" >> "${outfile}"
        return
    fi

    local canon_hash active_hash
    canon_hash=$(_safe_adb_root "sha256sum ${canonical} | awk '{print \$1}'" | tr -d '\r')
    active_hash=$(_safe_adb_root "sha256sum ${active} | awk '{print \$1}'" | tr -d '\r')

    if [[ "${canon_hash}" == "${active_hash}" ]]; then
        _mon_check "hosts_integrity" "ok" "sha256sum ${active}" \
            "Hosts file matches canonical (${active_hash:0:12}…)" "false" >> "${outfile}"
    else
        _mon_check "hosts_integrity" "error" "sha256sum ${active}" \
            "Hosts mismatch: active ${active_hash:0:12}… ≠ canonical ${canon_hash:0:12}…" \
            "true" >> "${outfile}"
    fi
}

# ---------------------------------------------------------------------------
# _check_dns OUTFILE
# ---------------------------------------------------------------------------
_check_dns() {
    local outfile="$1"
    local private_dns
    private_dns=$(_safe_adb_root "settings get global private_dns_mode" | tr -d '\r')
    if [[ "${private_dns}" == "off" || "${private_dns}" == "null" ]]; then
        _mon_check "dns_private_dns" "ok" "settings get global private_dns_mode" \
            "Private DNS is off (expected)" "false" >> "${outfile}"
    else
        _mon_check "dns_private_dns" "error" "settings get global private_dns_mode" \
            "Private DNS is ON (mode=${private_dns}) — DNS enforcement may be bypassed" \
            "true" >> "${outfile}"
    fi
}

# ---------------------------------------------------------------------------
# _check_launcher OUTFILE
# ---------------------------------------------------------------------------
_check_launcher() {
    local outfile="$1"
    local pkg="com.qqlabs.minimalistlauncher"
    if adb_root_shell "pm list packages -e ${pkg}" 2>/dev/null | grep -q "${pkg}"; then
        _mon_check "launcher_installed" "ok" "pm list packages -e ${pkg}" \
            "Minimalist launcher is installed and enabled" "false" >> "${outfile}"
    else
        _mon_check "launcher_installed" "fatal" "pm list packages -e ${pkg}" \
            "Minimalist launcher is NOT installed" "true" >> "${outfile}"
    fi
}

# ---------------------------------------------------------------------------
# _check_boot_persistence OUTFILE
# ---------------------------------------------------------------------------
_check_boot_persistence() {
    local outfile="$1"
    local boot_script="/data/adb/service.d/99-focus-mode.sh"
    if adb_root_shell "test -x ${boot_script}" >/dev/null 2>&1; then
        _mon_check "boot_persistence" "ok" "test -x ${boot_script}" \
            "Magisk boot script present and executable" "false" >> "${outfile}"
    else
        _mon_check "boot_persistence" "fatal" "test -x ${boot_script}" \
            "Magisk boot script missing or not executable at ${boot_script}" "true" >> "${outfile}"
    fi
}

# ---------------------------------------------------------------------------
# monitor_collect_snapshot SNAPSHOT_DIR
# Runs all checks and writes SNAPSHOT_DIR/report.json.
# ---------------------------------------------------------------------------
monitor_collect_snapshot() {
    local snapshot_dir="$1"
    mkdir -p "${snapshot_dir}"
    local tmp_checks
    tmp_checks=$(mktemp)
    trap 'rm -f "${tmp_checks}"' RETURN

    _info "Collecting monitoring snapshot → ${snapshot_dir}"

    _check_battery       "${tmp_checks}"
    _check_storage       "${tmp_checks}"
    _check_daemon "focus_daemon"    "pgrep -f focus_daemon.sh"    "${tmp_checks}"
    _check_daemon "hosts_enforcer"  "pgrep -f hosts_enforcer.sh"  "${tmp_checks}"
    _check_daemon "dns_enforcer"    "pgrep -f dns_enforcer.sh"    "${tmp_checks}"
    _check_daemon "launcher_enforcer" "pgrep -f launcher_enforcer.sh" "${tmp_checks}"
    _check_hosts_integrity  "${tmp_checks}"
    _check_dns              "${tmp_checks}"
    _check_launcher         "${tmp_checks}"
    _check_boot_persistence "${tmp_checks}"

    # Wrap lines into a JSON array
    {
        printf '{"timestamp":"%s","device":"%s","checks":[\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${ADB_SERIAL}"
        paste -sd ',' "${tmp_checks}"
        printf '\n]}\n'
    } > "${snapshot_dir}/report.json"

    cp "${snapshot_dir}/report.json" \
        "$(dirname "${snapshot_dir}")/latest.json" 2>/dev/null || true

    _info "Snapshot saved: ${snapshot_dir}/report.json"
}

# ---------------------------------------------------------------------------
# monitor_print_summary SNAPSHOT_DIR
# ---------------------------------------------------------------------------
monitor_print_summary() {
    local snapshot_dir="$1"
    local report="${snapshot_dir}/report.json"
    [[ -f "${report}" ]] || { _warn "No report found at ${report}"; return; }

    printf '\n=== Monitoring Summary ===\n'
    # Simple grep-based extraction (no jq required)
    local ok warn err fatal
    ok=$(grep -o '"status":"ok"'    "${report}" | wc -l)
    warn=$(grep -o '"status":"warn"'  "${report}" | wc -l)
    err=$(grep -o '"status":"error"' "${report}" | wc -l)
    fatal=$(grep -o '"status":"fatal"' "${report}" | wc -l)
    printf '  ok=%-3d  warn=%-3d  error=%-3d  fatal=%-3d\n' \
        "${ok}" "${warn}" "${err}" "${fatal}"

    if (( warn + err + fatal > 0 )); then
        printf '\nIssues found:\n'
        grep -o '"check":"[^"]*","status":"[^ok][^"]*","[^}]*"message":"[^"]*"' \
            "${report}" | sed 's/.*"check":"\([^"]*\)".*"status":"\([^"]*\)".*"message":"\([^"]*\)".*/  [\2] \1: \3/' \
            || grep '"status":"' "${report}" || true
    fi
    printf '==========================\n\n'
}

# ---------------------------------------------------------------------------
# monitor_severity_exit SNAPSHOT_DIR
# Returns 1 when any check has status fatal or error; 0 otherwise.
# Uses a precise regex matching only the "status" JSON key to avoid
# false positives from message text that contains the words "error" or "fatal".
# ---------------------------------------------------------------------------
monitor_severity_exit() {
    local snapshot_dir="$1"
    local report="${snapshot_dir}/report.json"
    [[ -f "${report}" ]] || return 0
    # "status":"error" and "status":"fatal" are emitted by _mon_check only for
    # the status field. Message values live under "message":"..." so this
    # pattern cannot collide with free-text content.
    if grep -qE '"status"\s*:\s*"(fatal|error)"' "${report}"; then
        return 1
    fi
    return 0
}
```

- [ ] **Step 3.2: Create the test file**

Create `phone_focus_mode/lib/tests/test_monitor.sh`:

```bash
#!/usr/bin/env bash
# Unit tests for monitor.sh helpers that do not require a real device.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Minimal stubs so sourcing monitor.sh does not blow up without ADB
adb_root_shell() { return 1; }
_info()  { :; }
_warn()  { :; }
_error() { :; }
_fatal() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }
_box()   { :; }
FORMAT_INDICATORS=()
FORMAT_DETECTION_MIN_MISSING=2
BATTERY_WARN_BELOW=20
STORAGE_WARN_BELOW_MB=500
ADB_SERIAL="test-serial"

source "${SCRIPT_DIR}/../monitor.sh"

PASS=0; FAIL=0
_t_pass() { PASS=$(( PASS + 1 )); printf '  OK: %s\n' "$1"; }
_t_fail() { FAIL=$(( FAIL + 1 )); printf '  FAIL: %s\n' "$1"; }

TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "${TMPDIR_TEST}"' EXIT

# --- _mon_check produces valid JSON-like line ---
line=$(_mon_check "test_check" "ok" "some_cmd" "all good" "false")
[[ "${line}" == *'"check":"test_check"'* ]] \
    && _t_pass "_mon_check outputs check name" \
    || _t_fail "_mon_check missing check name"
[[ "${line}" == *'"status":"ok"'* ]] \
    && _t_pass "_mon_check outputs status" \
    || _t_fail "_mon_check missing status"

# --- monitor_is_formatted returns 1 when no indicators are missing ---
# (FORMAT_INDICATORS is empty, so 0 missing < threshold 2)
if ! monitor_is_formatted 2>/dev/null; then
    _t_pass "monitor_is_formatted returns 1 when no indicators are missing"
else
    _t_fail "monitor_is_formatted should return 1 with empty FORMAT_INDICATORS"
fi

# --- monitor_severity_exit returns 0 on empty/no report ---
monitor_severity_exit "${TMPDIR_TEST}/nonexistent" \
    && _t_pass "monitor_severity_exit returns 0 when no report" \
    || _t_fail "monitor_severity_exit should return 0 for missing report"

# --- monitor_severity_exit returns 1 when fatal present ---
echo '{"checks":[{"check":"x","status":"fatal","source":"s","message":"m","repairable":false}]}' \
    > "${TMPDIR_TEST}/report.json"
if ! monitor_severity_exit "${TMPDIR_TEST}"; then
    _t_pass "monitor_severity_exit returns 1 on fatal"
else
    _t_fail "monitor_severity_exit should return 1 on fatal"
fi

# --- monitor_severity_exit returns 0 when all ok ---
echo '{"checks":[{"check":"x","status":"ok","source":"s","message":"m","repairable":false}]}' \
    > "${TMPDIR_TEST}/report.json"
monitor_severity_exit "${TMPDIR_TEST}" \
    && _t_pass "monitor_severity_exit returns 0 on all-ok" \
    || _t_fail "monitor_severity_exit should return 0 on all-ok"

printf '\nResults: %d passed, %d failed\n' "${PASS}" "${FAIL}"
[[ "${FAIL}" -eq 0 ]]
```

- [ ] **Step 3.3: Run the tests**

```bash
bash phone_focus_mode/lib/tests/test_monitor.sh
```

Expected: all tests pass.

- [ ] **Step 3.4: Run ShellCheck**

```bash
shellcheck --severity=warning phone_focus_mode/lib/monitor.sh
shellcheck --severity=warning phone_focus_mode/lib/tests/test_monitor.sh
```

- [ ] **Step 3.5: Commit**

```bash
git add phone_focus_mode/lib/monitor.sh phone_focus_mode/lib/tests/test_monitor.sh
git commit -m "feat(phone): add lib/monitor.sh — security and health monitoring"
```

---

## Chunk 4: Backup library — `lib/backup.sh`

### Files

- Create: `phone_focus_mode/lib/backup.sh`

### Background

`backup.sh` provides:

- `backup_make_snapshot_dir DEVICE_ID` → prints path of new timestamped snapshot dir
- `backup_device_info SNAPSHOT_DIR`
- `backup_security_state SNAPSHOT_DIR`
- `backup_apks SNAPSHOT_DIR`
- `backup_app_data SNAPSHOT_DIR`
- `backup_media SNAPSHOT_DIR`
- `backup_prune_history DEVICE_BACKUP_ROOT`
- `backup_run_incremental DEVICE_ID` — calls all steps above

All entries respect `restore_policy`. Items marked `manual_only` are backed up normally. `backup_only` are backed up but flagged with a note in the snapshot manifest.

---

- [ ] **Step 4.1: Create `lib/backup.sh`**

Create `phone_focus_mode/lib/backup.sh`:

```bash
#!/usr/bin/env bash
# lib/backup.sh — Incremental backup of APKs, app data, media, and security state.
# Requires: adb_common.sh and backup_manifest.sh sourced, ADB_SERIAL set.
set -euo pipefail

# ---------------------------------------------------------------------------
# backup_make_snapshot_dir DEVICE_ID → prints snapshot path
# ---------------------------------------------------------------------------
backup_make_snapshot_dir() {
    local device_id="$1"
    local ts
    ts=$(date -u +%Y%m%dT%H%M%SZ)
    local snapshot_dir="${PHONE_BACKUP_ROOT}/${device_id}/history/${ts}"
    mkdir -p \
        "${snapshot_dir}/device_info" \
        "${snapshot_dir}/security_state" \
        "${snapshot_dir}/apks" \
        "${snapshot_dir}/app_data" \
        "${snapshot_dir}/media" \
        "${snapshot_dir}/monitoring"
    printf '%s' "${snapshot_dir}"
}

# ---------------------------------------------------------------------------
# _backup_update_latest SNAPSHOT_DIR DEVICE_BACKUP_ROOT
# ---------------------------------------------------------------------------
_backup_update_latest() {
    local snapshot_dir="$1"
    local device_root="$2"
    local latest="${device_root}/latest"
    rm -f "${latest}"
    ln -s "${snapshot_dir}" "${latest}" 2>/dev/null \
        || cp -a "${snapshot_dir}/." "${latest}/"
}

# ---------------------------------------------------------------------------
# backup_device_info SNAPSHOT_DIR
# ---------------------------------------------------------------------------
backup_device_info() {
    local out="$1/device_info"
    _info "Backing up device info → ${out}"
    adb_cmd shell getprop                         > "${out}/getprop.txt" 2>/dev/null || true
    adb_cmd shell pm list packages -f             > "${out}/packages_full.txt" 2>/dev/null || true
    adb_cmd shell pm list packages                > "${out}/packages.txt" 2>/dev/null || true
    adb_cmd shell df                              > "${out}/df.txt" 2>/dev/null || true
    printf '%s\n' "${ADB_SERIAL}"                 > "${out}/serial.txt"
    adb_cmd shell getprop ro.product.model        > "${out}/model.txt" 2>/dev/null || true
    adb_cmd shell getprop ro.build.fingerprint    > "${out}/fingerprint.txt" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# backup_security_state SNAPSHOT_DIR
# ---------------------------------------------------------------------------
backup_security_state() {
    local out="$1/security_state"
    _info "Backing up security state → ${out}"
    for f in "${SECURITY_STATE_FILES[@]}"; do
        local dest="${out}$(dirname "${f}")"
        mkdir -p "${dest}"
        adb_root_shell "cat '${f}'" > "${dest}/$(basename "${f}")" 2>/dev/null || {
            _warn "Could not back up ${f} (may not exist yet)"
        }
    done
    # Daemon PIDs and status
    adb_root_shell "pgrep -a -f '(focus_daemon|hosts_enforcer|dns_enforcer|launcher_enforcer)'" \
        > "${out}/daemon_pids.txt" 2>/dev/null || true
    adb_root_shell "settings get global private_dns_mode" \
        > "${out}/private_dns_mode.txt" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# backup_apks SNAPSHOT_DIR
# ---------------------------------------------------------------------------
backup_apks() {
    local out="$1/apks"
    _info "Backing up APKs → ${out}"
    local entry pkg policy
    for entry in "${APK_ITEMS[@]}"; do
        pkg="${entry%%|*}"
        policy=$(printf '%s' "${entry}" | cut -d'|' -f2)

        local apk_path
        apk_path=$(adb_root_shell "pm path ${pkg} | head -1 | sed 's/package://'" \
            2>/dev/null | tr -d '\r' || true)

        if [[ -z "${apk_path}" ]]; then
            _warn "APK not found on device: ${pkg} (skipping)"
            continue
        fi

        local dest_dir="${out}/${pkg}"
        mkdir -p "${dest_dir}"
        adb_cmd pull "${apk_path}" "${dest_dir}/base.apk" 2>/dev/null \
            && _info "  Backed up ${pkg} (policy: ${policy})" \
            || _warn "  Failed to pull APK for ${pkg}"

        # Record policy alongside the APK
        printf '%s\n' "${policy}" > "${dest_dir}/restore_policy.txt"
    done
}

# ---------------------------------------------------------------------------
# _validate_pkg_name PKG — abort if package name contains unsafe characters
# ---------------------------------------------------------------------------
_validate_pkg_name() {
    local pkg="$1"
    [[ "${pkg}" =~ ^[A-Za-z0-9._-]+$ ]] \
        || _fatal "Unsafe package name rejected: '${pkg}'. Only [A-Za-z0-9._-] allowed."
}

# ---------------------------------------------------------------------------
# backup_app_data SNAPSHOT_DIR
# ---------------------------------------------------------------------------
backup_app_data() {
    local out="$1/app_data"
    _info "Backing up app data → ${out}"
    local entry pkg path policy parent_dir base_dir
    for entry in "${APP_DATA_ITEMS[@]}"; do
        pkg="${entry%%|*}"
        path=$(printf '%s' "${entry}" | cut -d'|' -f2)
        policy=$(printf '%s' "${entry}" | cut -d'|' -f3)

        # Validate package name before use in a root shell command
        _validate_pkg_name "${pkg}"

        local dest_dir="${out}/${pkg}"
        mkdir -p "${dest_dir}"

        if ! adb_root_shell "test -d '${path}'" >/dev/null 2>&1; then
            _warn "App data path not found: ${path} for ${pkg} (skipping)"
            continue
        fi

        parent_dir=$(dirname "${path}")
        base_dir=$(basename "${path}")
        # Build the tar command so the remote shell sees single-quoted path arguments,
        # preventing any on-device word-splitting or glob expansion.
        local tar_cmd="tar -czf - -C '${parent_dir}' '${base_dir}'"
        adb_root_shell "${tar_cmd}" \
            > "${dest_dir}/data.tar.gz" 2>/dev/null \
            && _info "  Backed up app data for ${pkg} (policy: ${policy})" \
            || _warn "  Failed to back up app data for ${pkg}"

        printf '%s\n' "${policy}" > "${dest_dir}/restore_policy.txt"
        [[ "${policy}" == "manual_only" ]] \
            && printf 'NOTE: manual_only — restore requires explicit operator action\n' \
               >> "${dest_dir}/restore_policy.txt"
    done
}

# ---------------------------------------------------------------------------
# backup_media SNAPSHOT_DIR
# ---------------------------------------------------------------------------
backup_media() {
    local out="$1/media"
    _info "Backing up media → ${out}"
    local entry name path policy
    for entry in "${MEDIA_ITEMS[@]}"; do
        name="${entry%%|*}"
        path=$(printf '%s' "${entry}" | cut -d'|' -f2)
        policy=$(printf '%s' "${entry}" | cut -d'|' -f3)

        local dest_dir="${out}/${name}"
        mkdir -p "${dest_dir}"

        adb_cmd pull "${path}" "${dest_dir}/" 2>/dev/null \
            && _info "  Backed up media/${name} from ${path} (policy: ${policy})" \
            || _warn "  Could not pull media/${name} from ${path} (may not exist)"
        printf '%s\n' "${policy}" > "${dest_dir}/restore_policy.txt"
    done
}

# ---------------------------------------------------------------------------
# backup_prune_history DEVICE_BACKUP_ROOT
# Removes history snapshots older than HISTORY_KEEP_DAYS.
# ---------------------------------------------------------------------------
backup_prune_history() {
    local device_root="$1"
    local history_dir="${device_root}/history"
    [[ -d "${history_dir}" ]] || return 0
    _info "Pruning history older than ${HISTORY_KEEP_DAYS} days in ${history_dir}"
    find "${history_dir}" -maxdepth 1 -mindepth 1 -type d \
        -mtime "+${HISTORY_KEEP_DAYS}" -print -exec rm -rf '{}' + || true
}

# ---------------------------------------------------------------------------
# backup_run_incremental DEVICE_ID
# Runs all backup steps and updates the latest/ pointer.
# ---------------------------------------------------------------------------
backup_run_incremental() {
    local device_id="$1"
    local device_root="${PHONE_BACKUP_ROOT}/${device_id}"
    local snapshot_dir
    snapshot_dir=$(backup_make_snapshot_dir "${device_id}")

    _info "Starting incremental backup to ${snapshot_dir}"
    backup_device_info    "${snapshot_dir}"
    backup_security_state "${snapshot_dir}"
    backup_apks           "${snapshot_dir}"
    backup_app_data       "${snapshot_dir}"
    backup_media          "${snapshot_dir}"
    _backup_update_latest "${snapshot_dir}" "${device_root}"
    backup_prune_history  "${device_root}"
    _info "Backup complete: ${snapshot_dir}"
    printf '%s' "${snapshot_dir}"
}
```

- [ ] **Step 4.2: Run ShellCheck**

```bash
shellcheck --severity=warning phone_focus_mode/lib/backup.sh
```

- [ ] **Step 4.3: Commit**

```bash
git add phone_focus_mode/lib/backup.sh
git commit -m "feat(phone): add lib/backup.sh — incremental APK/data/media/security backup"
```

---

## Chunk 5: Restore library — `lib/restore.sh`

### Files

- Create: `phone_focus_mode/lib/restore.sh`

### Background

`restore.sh` provides the restore actions used by `fresh-phone` mode. Each function respects the manifest's `restore_policy`.

Key functions:

- `restore_verify_prerequisites` — checks root, Magisk, ADB auth; fails with checklist if missing
- `restore_security_stack` — calls `deploy.sh` (the deployment primitive)
- `restore_apks BACKUP_DIR` — reinstalls APKs with `safe_restore` policy
- `restore_media BACKUP_DIR` — pushes media items back to device
- `restore_print_manual_steps BACKUP_DIR` — lists `manual_only` items the operator must handle

`restore.sh` never restores `manual_only` app data automatically. It prints the list of manual steps.

---

- [ ] **Step 5.1: Create `lib/restore.sh`**

Create `phone_focus_mode/lib/restore.sh`:

```bash
#!/usr/bin/env bash
# lib/restore.sh — Restore security stack, APKs, and media after format.
# Requires: adb_common.sh, backup_manifest.sh sourced, ADB_SERIAL set.
# deploy.sh path resolved relative to this library's parent directory.
set -euo pipefail

_PHONE_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---------------------------------------------------------------------------
# restore_verify_prerequisites
# Checks all prerequisites and prints a specific checklist if any are missing.
# Exits non-zero if prerequisites are not met.
# ---------------------------------------------------------------------------
restore_verify_prerequisites() {
    local -a problems=()

    # ADB connectivity
    if ! adb_cmd get-state >/dev/null 2>&1; then
        problems+=("ADB device not reachable. Ensure USB debugging is authorized or wireless ADB is paired.")
    fi

    # Root access
    if ! adb_root_shell "echo root_ok" 2>/dev/null | grep -q "root_ok"; then
        problems+=("Root shell failed. Ensure Magisk is installed and ADB root is authorized in Magisk settings.")
    fi

    if [[ ${#problems[@]} -gt 0 ]]; then
        _box "PREREQUISITES NOT MET — CANNOT CONTINUE" \
            "" \
            "Please resolve the following before running fresh-phone:" \
            "${problems[@]/#/  ✗ }" \
            "" \
            "Manual steps for a freshly formatted phone:" \
            "  1. Install Magisk from https://github.com/topjohnwu/Magisk" \
            "  2. In Magisk → Settings → enable 'Rooted Debugging'" \
            "  3. On phone: Settings → Developer options → enable 'USB Debugging'" \
            "  4. Authorize this PC on the phone when prompted" \
            "  5. Optionally pair wireless ADB: Settings → Developer options → Wireless debugging"
        return 1
    fi

    _info "All prerequisites verified"
}

# ---------------------------------------------------------------------------
# restore_security_stack
# Delegates entirely to deploy.sh — the deployment primitive.
# ---------------------------------------------------------------------------
restore_security_stack() {
    _info "Restoring security stack via deploy.sh"
    local deploy_script="${_PHONE_PROJECT_DIR}/deploy.sh"
    [[ -x "${deploy_script}" ]] \
        || _fatal "deploy.sh not found or not executable at ${deploy_script}"

    # deploy.sh uses ADB_SERIAL when set; existing PHONE_IP fallback preserved.
    env ADB_SERIAL="${ADB_SERIAL}" bash "${deploy_script}"
}

# ---------------------------------------------------------------------------
# restore_apks BACKUP_DIR
# Reinstalls APKs that have restore_policy=safe_restore.
# ---------------------------------------------------------------------------
restore_apks() {
    local backup_dir="$1"
    local apk_dir="${backup_dir}/apks"
    [[ -d "${apk_dir}" ]] || { _warn "No APK backup found at ${apk_dir}"; return 0; }

    _info "Restoring APKs from ${apk_dir}"
    local entry pkg policy apk
    for entry in "${APK_ITEMS[@]}"; do
        pkg="${entry%%|*}"
        policy=$(printf '%s' "${entry}" | cut -d'|' -f2)

        [[ "${policy}" == "safe_restore" ]] || {
            _info "  Skipping ${pkg} (policy: ${policy})"
            continue
        }

        apk="${apk_dir}/${pkg}/base.apk"
        if [[ ! -f "${apk}" ]]; then
            _warn "  APK not found in backup: ${pkg} (${apk})"
            continue
        fi

        _info "  Installing ${pkg}"
        adb_cmd install -r "${apk}" \
            && _info "  Installed ${pkg}" \
            || _warn "  Failed to install ${pkg}"
    done
}

# ---------------------------------------------------------------------------
# restore_media BACKUP_DIR
# Pushes back media items with restore_policy=safe_restore.
# ---------------------------------------------------------------------------
restore_media() {
    local backup_dir="$1"
    local media_dir="${backup_dir}/media"
    [[ -d "${media_dir}" ]] || { _warn "No media backup at ${media_dir}"; return 0; }

    _info "Restoring media from ${media_dir}"
    local entry name path policy
    for entry in "${MEDIA_ITEMS[@]}"; do
        name="${entry%%|*}"
        path=$(printf '%s' "${entry}" | cut -d'|' -f2)
        policy=$(printf '%s' "${entry}" | cut -d'|' -f3)

        [[ "${policy}" == "safe_restore" ]] || {
            _info "  Skipping media/${name} (policy: ${policy})"
            continue
        }

        local src="${media_dir}/${name}"
        [[ -d "${src}" ]] || {
            _warn "  Media backup not found: ${src}"
            continue
        }

        _info "  Pushing media/${name} → ${path}"
        adb_cmd push "${src}/." "${path}/" \
            && _info "  Restored media/${name}" \
            || _warn "  Failed to restore media/${name}"
    done
}

# ---------------------------------------------------------------------------
# restore_print_manual_steps BACKUP_DIR
# Lists all manual_only items the operator must handle.
# ---------------------------------------------------------------------------
restore_print_manual_steps() {
    local backup_dir="$1"
    local -a steps=()

    # App data: all manual_only in v1
    local entry pkg policy path
    for entry in "${APP_DATA_ITEMS[@]}"; do
        pkg="${entry%%|*}"
        path=$(printf '%s' "${entry}" | cut -d'|' -f2)
        policy=$(printf '%s' "${entry}" | cut -d'|' -f3)
        [[ "${policy}" == "manual_only" ]] \
            && steps+=("App data for ${pkg}: backup at ${backup_dir}/app_data/${pkg}/data.tar.gz")
    done

    # Secrets reminder
    steps+=("Re-enter coordinates in phone_focus_mode/config_secrets.sh if needed")
    steps+=("Re-authorize wireless ADB pairing if using it")
    steps+=("Verify Magisk modules are re-installed if any were in use")

    if [[ ${#steps[@]} -gt 0 ]]; then
        _box "MANUAL FOLLOW-UP STEPS REQUIRED" \
            "" \
            "The automated restore is complete. You must handle the following manually:" \
            "${steps[@]/#/  ▶ }"
    fi
}
```

- [ ] **Step 5.2: Run ShellCheck**

```bash
shellcheck --severity=warning phone_focus_mode/lib/restore.sh
```

- [ ] **Step 5.3: Commit**

```bash
git add phone_focus_mode/lib/restore.sh
git commit -m "feat(phone): add lib/restore.sh — safe APK/media restore and manual-step printer"
```

---

## Chunk 6: Orchestrator — `run_phone.sh` + `deploy.sh` refactor

### Files

- Create: `phone_focus_mode/run_phone.sh`
- Modify: `phone_focus_mode/deploy.sh` (add `ADB_SERIAL` support)

### Background

`run_phone.sh` is the main orchestrator. It:

1. Sources all library modules
2. Acquires the single-instance lock
3. Checks cooldown (for `auto` mode)
4. Calls the appropriate flow based on the subcommand argument
5. Exports `ADB_SERIAL` for all child processes including `deploy.sh`

`deploy.sh` currently uses `PHONE_IP` unconditionally. Adding `ADB_SERIAL` support means: if `ADB_SERIAL` is set, use `-s "${ADB_SERIAL}"` in `adb` calls instead of assuming the IP-based connection. The existing `PHONE_IP` path should still work as before.

---

- [ ] **Step 6.1: Read the current `deploy.sh` to understand its structure**

```bash
head -60 phone_focus_mode/deploy.sh
```

- [ ] **Step 6.2: Add `ADB_SERIAL` support to `deploy.sh`**

Find the section in `deploy.sh` that sets up the `adb` command (likely where `PHONE_IP` is used or where `adb connect` is called). Add the following early in the script, after the existing variable declarations:

```bash
# Support device targeting via ADB_SERIAL (set by run_phone.sh orchestrator).
# When ADB_SERIAL is set, skip the IP-based connect and use -s directly.
if [[ -n "${ADB_SERIAL:-}" ]]; then
    ADB_TARGET=(-s "${ADB_SERIAL}")
    _info "Using device serial from ADB_SERIAL: ${ADB_SERIAL}"
else
    ADB_TARGET=()
    # existing IP-based connection logic remains unchanged below
fi
```

Then ensure all `adb` invocations in `deploy.sh` use `adb "${ADB_TARGET[@]}" ...` instead of bare `adb ...`. Preserve existing behavior when `ADB_SERIAL` is not set.

> **Note:** Read `deploy.sh` in full (Step 6.1) before making this edit to understand exactly where the IP connection and adb calls are. Apply the minimum change needed.

- [ ] **Step 6.3: Run ShellCheck on modified `deploy.sh`**

```bash
shellcheck --severity=warning phone_focus_mode/deploy.sh
```

- [ ] **Step 6.4: Create `phone_focus_mode/run_phone.sh`**

Create `phone_focus_mode/run_phone.sh`:

```bash
#!/usr/bin/env bash
# run_phone.sh — Phone focus mode orchestrator.
#
# Usage:
#   run_phone.sh [auto]           Everyday: backup, monitor, repair minor drift.
#                                 If the phone looks formatted, shows a warning
#                                 and exits — does nothing else.
#   run_phone.sh fresh-phone      Full recovery after a factory reset.
#   run_phone.sh backup           Incremental backup only.
#   run_phone.sh monitor          Health and security snapshot only.
#   run_phone.sh doctor           Diagnose and repair drift without data restore.
#   run_phone.sh --help | -h      Show this help.
#
# Environment variables:
#   ADB_SERIAL          Target a specific device by serial.
#   PHONE_BACKUP_ROOT   Override backup root (default: ~/phone_backups).
#   PHONE_IP            Wireless ADB host (used by deploy.sh when ADB_SERIAL unset).
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Source libraries
# ---------------------------------------------------------------------------
# shellcheck source=lib/adb_common.sh
source "${_SCRIPT_DIR}/lib/adb_common.sh"
# shellcheck source=backup_manifest.sh
source "${_SCRIPT_DIR}/backup_manifest.sh"
# shellcheck source=lib/monitor.sh
source "${_SCRIPT_DIR}/lib/monitor.sh"
# shellcheck source=lib/backup.sh
source "${_SCRIPT_DIR}/lib/backup.sh"
# shellcheck source=lib/restore.sh
source "${_SCRIPT_DIR}/lib/restore.sh"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
SUBCOMMAND="${1:-auto}"
shift 2>/dev/null || true

case "${SUBCOMMAND}" in
    --help|-h|help)
        grep '^#' "${BASH_SOURCE[0]}" | grep -v '^#!/' | sed 's/^# \?//'
        exit 0
        ;;
    auto|fresh-phone|backup|monitor|doctor) ;;
    *)
        _fatal "Unknown subcommand: '${SUBCOMMAND}'. Run with --help for usage."
        ;;
esac

# ---------------------------------------------------------------------------
# Shared setup: device selection, lock, identity
# ---------------------------------------------------------------------------
_setup_common() {
    adb_select_device "${ADB_SERIAL:-}"
    adb_verify_root
    adb_verify_trusted_identity
    adb_collect_identity
}

# ---------------------------------------------------------------------------
# cmd_auto — everyday maintenance
# ---------------------------------------------------------------------------
cmd_auto() {
    adb_acquire_lock

    if ! adb_check_cooldown "${COOLDOWN_AUTO_SECS}" "auto"; then
        _info "auto: cooldown active, nothing to do."
        exit 0
    fi

    _setup_common

    # Step 1: Format detection
    local -a missing
    mapfile -t missing < <(monitor_check_format_indicators)
    local missing_count="${#missing[@]}"
    if (( missing_count >= FORMAT_DETECTION_MIN_MISSING )); then
        monitor_print_format_warning "${missing[@]}"
        exit 2
    fi

    # Step 2: Monitoring snapshot
    local device_id="${ADB_SERIAL//[^a-zA-Z0-9_-]/_}"
    local snapshot_dir="${PHONE_BACKUP_ROOT}/${device_id}/monitoring/$(date -u +%Y%m%dT%H%M%SZ)"
    monitor_collect_snapshot "${snapshot_dir}"

    # Step 3: Incremental backup
    backup_run_incremental "${device_id}"

    # Step 4: Minor repair (allowed repairs only)
    _auto_repair_minor_drift "${snapshot_dir}"

    # Step 5: Summary
    monitor_print_summary "${snapshot_dir}"
    adb_mark_last_run "auto"
    monitor_severity_exit "${snapshot_dir}" || exit 1
}

# ---------------------------------------------------------------------------
# _auto_repair_minor_drift SNAPSHOT_DIR
# Only restarts daemons when scripts already exist on-device. Never deploys.
# ---------------------------------------------------------------------------
_auto_repair_minor_drift() {
    local snapshot_dir="$1"
    local report="${snapshot_dir}/report.json"
    [[ -f "${report}" ]] || return 0

    local repaired=0
    # If daemons are missing but boot script exists — re-source the boot script
    if grep -q '"check":"focus_daemon","status":"error"' "${report}" 2>/dev/null; then
        if adb_root_shell "test -x /data/adb/service.d/99-focus-mode.sh" >/dev/null 2>&1; then
            _info "Repair: restarting focus daemons via boot script"
            adb_root_shell "sh /data/adb/service.d/99-focus-mode.sh" >/dev/null 2>&1 || true
            repaired=$(( repaired + 1 ))
        else
            _warn "Cannot restart daemons: boot script missing. Run 'fresh-phone' or 'doctor'."
        fi
    fi
    [[ ${repaired} -gt 0 ]] && _info "Minor repairs applied: ${repaired}" || true
}

# ---------------------------------------------------------------------------
# cmd_fresh_phone — full recovery after format
# ---------------------------------------------------------------------------
cmd_fresh_phone() {
    _info "=== fresh-phone: Full recovery mode ==="
    adb_select_device "${ADB_SERIAL:-}"

    # Prerequisites must be met before we touch anything
    restore_verify_prerequisites

    adb_collect_identity
    local device_id="${ADB_SERIAL//[^a-zA-Z0-9_-]/_}"
    local backup_root="${PHONE_BACKUP_ROOT}/${device_id}/latest"

    if [[ ! -d "${backup_root}" ]]; then
        _fatal "No backup found at ${backup_root}. Cannot restore without a prior backup."
    fi

    # Pre-change snapshot
    local pre_snapshot="${PHONE_BACKUP_ROOT}/${device_id}/monitoring/pre_restore_$(date -u +%Y%m%dT%H%M%SZ)"
    monitor_collect_snapshot "${pre_snapshot}" || true

    # Restore in priority order (spec §Restore priority order)
    restore_security_stack              # delegates to deploy.sh
    restore_apks    "${backup_root}"
    restore_media   "${backup_root}"

    # Post-restore monitoring snapshot
    local post_snapshot="${PHONE_BACKUP_ROOT}/${device_id}/monitoring/post_restore_$(date -u +%Y%m%dT%H%M%SZ)"
    monitor_collect_snapshot "${post_snapshot}" || true
    monitor_print_summary    "${post_snapshot}"

    # Save trusted device record now that setup is complete
    adb_save_trusted_device

    # Manual steps
    restore_print_manual_steps "${backup_root}"
}

# ---------------------------------------------------------------------------
# cmd_backup — incremental backup only
# ---------------------------------------------------------------------------
cmd_backup() {
    _setup_common
    local device_id="${ADB_SERIAL//[^a-zA-Z0-9_-]/_}"
    backup_run_incremental "${device_id}"
}

# ---------------------------------------------------------------------------
# cmd_monitor — health snapshot only
# ---------------------------------------------------------------------------
cmd_monitor() {
    _setup_common
    local device_id="${ADB_SERIAL//[^a-zA-Z0-9_-]/_}"
    local snapshot_dir="${PHONE_BACKUP_ROOT}/${device_id}/monitoring/$(date -u +%Y%m%dT%H%M%SZ)"
    monitor_collect_snapshot "${snapshot_dir}"
    monitor_print_summary    "${snapshot_dir}"
    monitor_severity_exit    "${snapshot_dir}" || exit 1
}

# ---------------------------------------------------------------------------
# cmd_doctor — diagnose and repair drift
# ---------------------------------------------------------------------------
cmd_doctor() {
    _setup_common
    local device_id="${ADB_SERIAL//[^a-zA-Z0-9_-]/_}"
    local snapshot_dir="${PHONE_BACKUP_ROOT}/${device_id}/monitoring/doctor_$(date -u +%Y%m%dT%H%M%SZ)"
    monitor_collect_snapshot "${snapshot_dir}"

    local report="${snapshot_dir}/report.json"
    local repaired=0

    # Restart daemons
    for daemon in focus_daemon hosts_enforcer dns_enforcer launcher_enforcer; do
        if grep -q "\"check\":\"${daemon}\",\"status\":\"error\"" "${report}" 2>/dev/null; then
            _info "Doctor: restarting ${daemon}"
            adb_root_shell "pgrep -f ${daemon}.sh | xargs kill -9 2>/dev/null || true" >/dev/null 2>&1 || true
            adb_root_shell "nohup sh /data/adb/focus_mode/${daemon}.sh </dev/null >/dev/null 2>&1 &" \
                >/dev/null 2>&1 || _warn "Could not restart ${daemon}"
            repaired=$(( repaired + 1 ))
        fi
    done

    # Re-deploy security stack when boot script is missing
    if grep -q '"check":"boot_persistence","status":"fatal"' "${report}" 2>/dev/null; then
        _info "Doctor: boot script missing — re-running deploy.sh"
        restore_security_stack
        repaired=$(( repaired + 1 ))
    fi

    # Re-push hosts/DNS if integrity checks failed and backing files exist
    if grep -q '"check":"hosts_integrity","status":"error"' "${report}" 2>/dev/null; then
        if [[ -f "${PHONE_BACKUP_ROOT}/${device_id}/latest/security_state/data/adb/focus_mode/hosts.canonical" ]]; then
            _info "Doctor: restoring canonical hosts from backup"
            adb_cmd push \
                "${PHONE_BACKUP_ROOT}/${device_id}/latest/security_state/data/adb/focus_mode/hosts.canonical" \
                "/data/adb/focus_mode/hosts.canonical"
            repaired=$(( repaired + 1 ))
        else
            _warn "Doctor: hosts integrity failed but no backup copy available. Run fresh-phone."
        fi
    fi

    # Post-repair snapshot
    monitor_collect_snapshot "${snapshot_dir}_after"
    monitor_print_summary    "${snapshot_dir}_after"

    _info "Doctor complete. Repairs applied: ${repaired}"
    monitor_severity_exit "${snapshot_dir}_after" || {
        _warn "Unresolved issues remain after doctor run."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
case "${SUBCOMMAND}" in
    auto)        cmd_auto        ;;
    fresh-phone) cmd_fresh_phone ;;
    backup)      cmd_backup      ;;
    monitor)     cmd_monitor     ;;
    doctor)      cmd_doctor      ;;
esac
```

- [ ] **Step 6.5: Make it executable**

```bash
chmod +x phone_focus_mode/run_phone.sh
```

- [ ] **Step 6.6: Run ShellCheck**

```bash
shellcheck --severity=warning phone_focus_mode/run_phone.sh
```

- [ ] **Step 6.7: Smoke test (no device required)**

```bash
bash phone_focus_mode/run_phone.sh --help
```

Expected: prints usage text without errors.

- [ ] **Step 6.8: Commit**

```bash
git add phone_focus_mode/run_phone.sh phone_focus_mode/deploy.sh
git commit -m "feat(phone): add run_phone.sh orchestrator; add ADB_SERIAL support to deploy.sh"
```

---

## Chunk 7: Visible entrypoint + systemd + README

### Files

- Create: `scripts/run_all/run_phone.sh`
- Create: `phone_focus_mode/systemd/phone-auto-sync.service`
- Create: `phone_focus_mode/systemd/phone-auto-sync.timer`
- Create: `phone_focus_mode/systemd/install_pc_phone_automation.sh`
- Modify (create if absent): `phone_focus_mode/README.md`

---

- [ ] **Step 7.1: Create `scripts/run_all/` and the visible wrapper**

```bash
mkdir -p scripts/run_all
```

Create `scripts/run_all/run_phone.sh`:

```bash
#!/usr/bin/env bash
# run_phone.sh — Visible entrypoint for the phone focus mode workflow.
#
# Quick reference:
#   ./scripts/run_all/run_phone.sh                  Everyday: backup + monitor + minor repair.
#                                                   Shows a warning if the phone was wiped.
#   ./scripts/run_all/run_phone.sh fresh-phone      Full recovery after a factory reset.
#   ./scripts/run_all/run_phone.sh doctor           Diagnose and repair security drift.
#   ./scripts/run_all/run_phone.sh backup           Incremental backup only.
#   ./scripts/run_all/run_phone.sh monitor          Health snapshot only.
#   ./scripts/run_all/run_phone.sh --help           Show full usage.
set -euo pipefail

_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_IMPL="${_REPO_ROOT}/phone_focus_mode/run_phone.sh"

if [[ ! -x "${_IMPL}" ]]; then
    printf 'ERROR: implementation script not found or not executable: %s\n' "${_IMPL}" >&2
    exit 1
fi

exec bash "${_IMPL}" "$@"
```

- [ ] **Step 7.2: Make it executable**

```bash
chmod +x scripts/run_all/run_phone.sh
```

- [ ] **Step 7.3: Smoke test the wrapper**

```bash
./scripts/run_all/run_phone.sh --help
```

Expected: prints the usage block from `phone_focus_mode/run_phone.sh`.

- [ ] **Step 7.4: Create systemd user service**

Create `phone_focus_mode/systemd/phone-auto-sync.service`:

```ini
[Unit]
Description=Phone focus mode auto sync
After=network.target

[Service]
Type=oneshot
ExecStart=%h/testsAndMisc/scripts/run_all/run_phone.sh auto
StandardOutput=journal
StandardError=journal
```

- [ ] **Step 7.5: Create systemd user timer**

Create `phone_focus_mode/systemd/phone-auto-sync.timer`:

```ini
[Unit]
Description=Run phone focus mode auto sync periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 7.6: Create the installer script**

Create `phone_focus_mode/systemd/install_pc_phone_automation.sh`:

```bash
#!/usr/bin/env bash
# install_pc_phone_automation.sh — Install user-level systemd automation for
# periodic phone sync. Runs as the current user (no sudo required).
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

mkdir -p "${_SYSTEMD_USER_DIR}"

cp "${_SCRIPT_DIR}/phone-auto-sync.service" "${_SYSTEMD_USER_DIR}/"
cp "${_SCRIPT_DIR}/phone-auto-sync.timer"   "${_SYSTEMD_USER_DIR}/"

systemctl --user daemon-reload
systemctl --user enable --now phone-auto-sync.timer

printf 'Installed and enabled phone-auto-sync.timer\n'
printf 'Next run: '
systemctl --user list-timers phone-auto-sync.timer --no-legend \
    | awk '{print $1, $2}' || printf '(check with: systemctl --user list-timers)\n'
```

- [ ] **Step 7.7: Make installer executable**

```bash
chmod +x phone_focus_mode/systemd/install_pc_phone_automation.sh
```

- [ ] **Step 7.8: Run ShellCheck on all new scripts**

```bash
shellcheck --severity=warning scripts/run_all/run_phone.sh
shellcheck --severity=warning phone_focus_mode/systemd/install_pc_phone_automation.sh
```

- [ ] **Step 7.9: Create/update `phone_focus_mode/README.md`**

Create `phone_focus_mode/README.md`:

````markdown
---
post_title: "Phone focus mode"
author1: "kuhy"
post_slug: "phone-focus-mode"
microsoft_alias: ""
featured_image: ""
categories:
  - "Documentation"
tags:
  - "android"
  - "adb"
  - "shell"
ai_note: "AI-assisted documentation"
summary: "One-command Android hardening management: backup, monitoring, and full recovery after a factory reset."
post_date: "2026-05-01"
---

## What is this?

A rooted-Android management system that enforces focus-mode restrictions,
monitors security and health, takes incremental backups, and can fully
restore a freshly formatted phone to its hardened state.

## Quick reference

Run the visible entrypoint from the repository root:

```bash
./scripts/run_all/run_phone.sh
```
````

### Normal day

```bash
./scripts/run_all/run_phone.sh
```

Takes an incremental backup, collects health and security status, repairs
minor drift, and prints a summary. If the phone looks wiped, shows a warning
and suggests `fresh-phone` instead — it never automatically restores data.

### After a factory reset

```bash
./scripts/run_all/run_phone.sh fresh-phone
```

Full recovery: verifies root and prerequisites, restores the security stack
via `deploy.sh`, reinstalls APKs, restores media, and lists remaining manual
steps (such as app data that requires manual restore).

### If something feels wrong

```bash
./scripts/run_all/run_phone.sh doctor
```

Inspects all security and health checks, attempts low-risk repairs (restarting
daemons, re-pushing hosts, re-deploying the security stack if the boot script
is missing), and clearly lists repaired vs unresolved issues.

### Other modes

```bash
./scripts/run_all/run_phone.sh backup    # Incremental backup only
./scripts/run_all/run_phone.sh monitor   # Health snapshot only
./scripts/run_all/run_phone.sh --help    # Full usage
```

## Backup storage

Backups are stored outside the repository:

```
~/phone_backups/<device-serial>/
  latest/               → symlink to newest snapshot
  history/<timestamp>/  → full snapshots
    device_info/
    security_state/
    apks/
    app_data/           (all manual_only in v1)
    media/
    monitoring/
```

Override the root with: `export PHONE_BACKUP_ROOT=/path/to/backups`

## Security stack components

| Script                 | Purpose                                                  |
| ---------------------- | -------------------------------------------------------- |
| `deploy.sh`            | Deployment primitive: pushes all scripts, starts daemons |
| `focus_daemon.sh`      | On-device: GPS-based focus enforcement                   |
| `hosts_enforcer.sh`    | On-device: protects `/system/etc/hosts`                  |
| `dns_enforcer.sh`      | On-device: forces Private DNS off, blocks DoH/DoT        |
| `launcher_enforcer.sh` | On-device: keeps approved launcher pinned                |
| `magisk_service.sh`    | Boot persistence via Magisk `service.d`                  |

## PC automation

Install periodic auto-sync (runs every 30 minutes when phone is available):

```bash
bash phone_focus_mode/systemd/install_pc_phone_automation.sh
```

## Configuration

Edit `phone_focus_mode/backup_manifest.sh` to change:

- which APKs are snapshotted and restored
- which app-data directories are captured
- which media directories are synced
- format-detection thresholds and cooldown settings

Secrets (GPS coordinates) live in `phone_focus_mode/config_secrets.sh`
(gitignored, must be created manually on each machine).

````

- [ ] **Step 7.10: Run pre-commit on all new/modified files**

```bash
pre-commit run --files \
    scripts/run_all/run_phone.sh \
    phone_focus_mode/run_phone.sh \
    phone_focus_mode/lib/adb_common.sh \
    phone_focus_mode/lib/monitor.sh \
    phone_focus_mode/lib/backup.sh \
    phone_focus_mode/lib/restore.sh \
    phone_focus_mode/backup_manifest.sh \
    phone_focus_mode/systemd/install_pc_phone_automation.sh \
    phone_focus_mode/README.md
````

Fix any issues found before proceeding.

- [ ] **Step 7.11: Commit**

```bash
git add \
    scripts/run_all/run_phone.sh \
    phone_focus_mode/systemd/ \
    phone_focus_mode/README.md
git commit -m "feat(phone): add visible wrapper, systemd automation, and README"
```

---

## Chunk 8: Live verification on the phone

> **Prerequisite:** Phone connected via USB or wireless ADB.

- [ ] **Step 8.1: Verify `--help` works end-to-end**

```bash
./scripts/run_all/run_phone.sh --help
```

- [ ] **Step 8.2: Run `monitor` to confirm ADB reaches the device**

```bash
./scripts/run_all/run_phone.sh monitor
```

Inspect output. Fix any shellcheck or runtime issues found.

- [ ] **Step 8.3: Run `backup` to confirm backup writes to `~/phone_backups/`**

```bash
./scripts/run_all/run_phone.sh backup
ls ~/phone_backups/
```

- [ ] **Step 8.4: Run `auto` to confirm format-detection and normal flow both work**

```bash
./scripts/run_all/run_phone.sh auto
```

- [ ] **Step 8.5: Simulate a format-detected scenario (dry run)**

Temporarily add a non-existent indicator to `FORMAT_INDICATORS` in
`backup_manifest.sh`, run `auto`, confirm the warning box appears and the
script exits without doing anything else. Revert the temporary change after.

- [ ] **Step 8.6: Final pre-commit pass**

```bash
pre-commit run --all-files
```

Fix any issues.

- [ ] **Step 8.7: Final commit if needed**

```bash
git add -A
git commit -m "chore(phone): final pre-commit fixes and live-verification adjustments"
```

---

## Summary of all files created/modified

| Path                                                      | Action                      |
| --------------------------------------------------------- | --------------------------- |
| `phone_focus_mode/lib/adb_common.sh`                      | Create                      |
| `phone_focus_mode/lib/monitor.sh`                         | Create                      |
| `phone_focus_mode/lib/backup.sh`                          | Create                      |
| `phone_focus_mode/lib/restore.sh`                         | Create                      |
| `phone_focus_mode/lib/tests/test_adb_common.sh`           | Create                      |
| `phone_focus_mode/lib/tests/test_monitor.sh`              | Create                      |
| `phone_focus_mode/backup_manifest.sh`                     | Create                      |
| `phone_focus_mode/run_phone.sh`                           | Create                      |
| `phone_focus_mode/deploy.sh`                              | Modify (ADB_SERIAL support) |
| `phone_focus_mode/systemd/phone-auto-sync.service`        | Create                      |
| `phone_focus_mode/systemd/phone-auto-sync.timer`          | Create                      |
| `phone_focus_mode/systemd/install_pc_phone_automation.sh` | Create                      |
| `phone_focus_mode/README.md`                              | Create                      |
| `scripts/run_all/run_phone.sh`                            | Create                      |

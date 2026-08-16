#!/bin/bash
# Regression tests for i3blocks hot-path efficiency fixes.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
I3BLOCKS_DIR="$REPO_DIR/scripts/periodic_background/i3-configuration/i3blocks"
CONFIG_FILE="$I3BLOCKS_DIR/config"

printf 'Running persist_common helper regression checks...\n'
bash "$SCRIPT_DIR/test_i3blocks_persist_common.sh"

TMP_DIR=$(mktemp -d)
BIN_DIR="$TMP_DIR/bin"
mkdir -p "$BIN_DIR"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_equals() {
  local expected="$1"
  local actual="$2"
  local context="$3"
  if [[ "$expected" != "$actual" ]]; then
    fail "$context (expected: '$expected', actual: '$actual')"
  fi
}

assert_le() {
  local actual="$1"
  local expected_max="$2"
  local context="$3"
  if (( actual > expected_max )); then
    fail "$context (expected <= $expected_max, actual: $actual)"
  fi
}

epoch_utc() {
  TZ=UTC date -d "$1" +%s
}

count_execs() {
  local script_path="$1"
  local log_file="$TMP_DIR/trace.log"
  PATH="$BIN_DIR:$PATH" strace -f -o "$log_file" -e trace=execve bash "$script_path" \
    >/dev/null 2>&1
  grep -c 'execve(' "$log_file"
}

cat >"$BIN_DIR/pacman" <<'EOF'
#!/bin/bash
exit 1
EOF
chmod +x "$BIN_DIR/pacman"

cat >"$BIN_DIR/pgrep" <<'EOF'
#!/bin/bash
exit 1
EOF
chmod +x "$BIN_DIR/pgrep"

cat >"$BIN_DIR/iw" <<'EOF'
#!/bin/bash
set -euo pipefail

if [[ $# -eq 1 && $1 == dev ]]; then
  if [[ ${WIFI_HAS_INTERFACE:-1} == 1 ]]; then
    printf '%s\n' \
      'phy#0' \
      '    Interface wlan0'
  fi
  exit 0
fi

if [[ $# -eq 3 && $1 == dev && $3 == link ]]; then
  if [[ ${WIFI_CONNECTED:-1} == 1 ]]; then
    printf '%s\n' \
      'Connected to 00:11:22:33:44:55 (on wlan0)' \
      'SSID: TestWifi' \
      'signal: -53 dBm'
  else
    printf '%s\n' 'Not connected.'
  fi
  exit 0
fi

printf 'unexpected iw args: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$BIN_DIR/iw"

cat >"$BIN_DIR/ip" <<'EOF'
#!/bin/bash
set -euo pipefail

if [[ $# -ge 8 && $1 == -o && $2 == -4 && $3 == addr && $4 == show ]]; then
  printf '%s\n' '3: wlan0    inet 192.168.1.44/24 brd 192.168.1.255 scope global dynamic wlan0'
  exit 0
fi

printf 'unexpected ip args: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$BIN_DIR/ip"

cat >"$BIN_DIR/df" <<'EOF'
#!/bin/bash
set -euo pipefail

if [[ $# -eq 2 && $1 == -h && $2 == / ]]; then
  printf '%s\n' \
    'Filesystem      Size  Used Avail Use% Mounted on' \
    '/dev/nvme0n1p2  100G   15G   80G  16% /'
  exit 0
fi

printf 'unexpected df args: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$BIN_DIR/df"

# Two blocks of checks live in libs to keep this file under the 250-line cap.
# They run in this shell and use the helpers and paths set up above. The fake
# $BIN_DIR binaries and their heredocs stay here: a seam inside a heredoc
# produces a lib that will not parse.
LIB_DIR="$SCRIPT_DIR/lib"
# shellcheck source=lib/i3blocks_config_checks.sh
source "$LIB_DIR/i3blocks_config_checks.sh"
# shellcheck source=lib/i3blocks_claude_usage.sh
source "$LIB_DIR/i3blocks_claude_usage.sh"

i3_tests_config_and_guards
i3_tests_claude_usage

printf 'Checking disk block behavior and fork count...\n'
disk_output=$(PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/disk.sh")
assert_equals '💾 15G/100G' "$disk_output" \
  'disk script should show used and total disk space'
assert_le "$(count_execs "$I3BLOCKS_DIR/disk.sh")" 2 \
  'disk script should stay at one external helper plus bash'

printf 'Checking PC startup block behavior and fork count...\n'
pc_live_epoch=$(epoch_utc '2026-05-01 06:30:00')
pc_live_output=$(TZ=UTC NOW_EPOCH="$pc_live_epoch" UPTIME_SECONDS=1800 PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/pc_startup_status.sh")
assert_equals 'PC:live' "$(printf '%s\n' "$pc_live_output" | sed -n '1p')" \
  'pc startup script should show live during the monitored startup window'
assert_le "$(count_execs "$I3BLOCKS_DIR/pc_startup_status.sh")" 1 \
  'pc startup script should avoid date and text-processing helpers'

pc_ok_epoch=$(epoch_utc '2026-05-01 10:00:00')
pc_ok_output=$(TZ=UTC NOW_EPOCH="$pc_ok_epoch" UPTIME_SECONDS=14400 PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/pc_startup_status.sh")
assert_equals 'PC:ok' "$(printf '%s\n' "$pc_ok_output" | sed -n '1p')" \
  'pc startup script should show ok when boot happened inside the startup window'

pc_warn_epoch=$(epoch_utc '2026-05-01 10:00:00')
pc_warn_output=$(TZ=UTC NOW_EPOCH="$pc_warn_epoch" UPTIME_SECONDS=1800 PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/pc_startup_status.sh")
assert_equals 'PC:warn' "$(printf '%s\n' "$pc_warn_output" | sed -n '1p')" \
  'pc startup script should warn when boot happened outside the startup window'

pc_skip_epoch=$(epoch_utc '2026-04-30 10:00:00')
pc_skip_output=$(TZ=UTC NOW_EPOCH="$pc_skip_epoch" UPTIME_SECONDS=1800 PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/pc_startup_status.sh")
assert_equals 'PC:skip' "$(printf '%s\n' "$pc_skip_output" | sed -n '1p')" \
  'pc startup script should skip on unmonitored days'

printf 'Checking shutdown countdown behavior and fork count...\n'
shutdown_config_file="$TMP_DIR/shutdown-schedule.conf"
cat >"$shutdown_config_file" <<'EOF'
MON_WED_HOUR=23
THU_SUN_HOUR=21
EOF

# Isolate from the machine's real override file so these assertions are hermetic.
shutdown_overrides_empty="$TMP_DIR/shutdown-overrides-empty.conf"
: > "$shutdown_overrides_empty"

# 2026-05-01 is a Friday -> THU_SUN_HOUR=21 applies; at 19:30 the next shutdown
# is 21:00. The block shows the exact clock time of the shutdown, not a
# relative countdown.
shutdown_countdown_epoch=$(epoch_utc '2026-05-01 19:30:00')
shutdown_countdown_output=$(TZ=UTC NOW_EPOCH="$shutdown_countdown_epoch" SHUTDOWN_CONFIG="$shutdown_config_file" OVERRIDES_FILE="$shutdown_overrides_empty" PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/shutdown_countdown.sh")
assert_equals '⏻ 21:00' "$(printf '%s\n' "$shutdown_countdown_output" | sed -n '1p')" \
  'shutdown countdown should show the exact clock time of the next shutdown'
assert_equals '#F1FA8C' "$(printf '%s\n' "$shutdown_countdown_output" | sed -n '3p')" \
  'shutdown countdown should show yellow for two hours or less remaining'
assert_le "$(count_execs "$I3BLOCKS_DIR/shutdown_countdown.sh")" 1 \
  'shutdown countdown should avoid date helpers in the hot path'

shutdown_window_epoch=$(epoch_utc '2026-05-01 21:15:00')
shutdown_window_output=$(TZ=UTC NOW_EPOCH="$shutdown_window_epoch" SHUTDOWN_CONFIG="$shutdown_config_file" OVERRIDES_FILE="$shutdown_overrides_empty" PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/shutdown_countdown.sh")
assert_equals '⏻ SHUTDOWN' "$(printf '%s\n' "$shutdown_window_output" | sed -n '1p')" \
  'shutdown countdown should show SHUTDOWN inside the blocked window'

# An active override (shutdown-override-manager.sh) rescues the shutdown: the
# block should show the overridden end time in green instead of a countdown or
# a SHUTDOWN warning. Window 19:00-23:00 covers the 19:30 sample time.
shutdown_overrides_active="$TMP_DIR/shutdown-overrides-active.conf"
override_start=$(epoch_utc '2026-05-01 19:00:00')
override_end=$(epoch_utc '2026-05-01 23:00:00')
printf '%s|%s|%s|%s\n' "$override_start" "$override_end" "$override_start" 'regression test override' > "$shutdown_overrides_active"
shutdown_override_output=$(TZ=UTC NOW_EPOCH="$shutdown_countdown_epoch" SHUTDOWN_CONFIG="$shutdown_config_file" OVERRIDES_FILE="$shutdown_overrides_active" PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/shutdown_countdown.sh")
assert_equals '▶ 23:00 (override)' "$(printf '%s\n' "$shutdown_override_output" | sed -n '1p')" \
  'shutdown countdown should show the overridden end time when an override is active'
assert_equals '#50FA7B' "$(printf '%s\n' "$shutdown_override_output" | sed -n '3p')" \
  'shutdown countdown should show green while an override is active'

printf 'All i3blocks efficiency regression tests passed.\n'

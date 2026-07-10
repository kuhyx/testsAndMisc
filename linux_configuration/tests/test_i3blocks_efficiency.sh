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
  if [[ -n "${AW_PID:-}" ]]; then
    kill "$AW_PID" 2>/dev/null || true
    wait "$AW_PID" 2>/dev/null || true
  fi
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

cat >"$BIN_DIR/bluetoothctl" <<'EOF'
#!/bin/bash
printf '%s\n' \
  'Device AA:BB:CC:DD:EE:FF' \
  'Alias: Test Headphones' \
  'Connected: yes'
EOF
chmod +x "$BIN_DIR/bluetoothctl"

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

cat >"$BIN_DIR/warp-cli" <<'EOF'
#!/bin/bash
set -euo pipefail

if [[ $# -eq 1 && $1 == status ]]; then
  printf 'Status update: %s\n' "${WARP_STATUS:-Disconnected}"
  exit 0
fi

printf 'unexpected warp-cli args: %s\n' "$*" >&2
exit 1
EOF
chmod +x "$BIN_DIR/warp-cli"

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

ln -s /bin/sleep "$BIN_DIR/aw-qt"

printf 'Checking config uses dedicated low-fork scripts...\n'
grep -q '^command=~/.config/i3blocks/time.sh$' "$CONFIG_FILE" \
  || fail 'time block should call time.sh'
grep -q '^interval=persist$' "$CONFIG_FILE" \
  || fail 'config should use persist interval for time block'
grep -q '^command=~/.config/i3blocks/memory.sh$' "$CONFIG_FILE" \
  || fail 'memory block should call memory.sh'
grep -q '^command=~/.config/i3blocks/ethernet.sh$' "$CONFIG_FILE" \
  || fail 'ethernet block should call ethernet.sh'
grep -q '^command=~/.config/i3blocks/disk.sh$' "$CONFIG_FILE" \
  || fail 'disk block should call disk.sh'
grep -q '^interval=10$' "$CONFIG_FILE" \
  || fail 'cpu block should poll at 10s interval'
grep -A2 '^\[motherboard_temperature\]$' "$CONFIG_FILE" | grep -q '^interval=30$' \
  || fail 'motherboard block should poll at 30s interval'
grep -A2 '^\[memory\]$' "$CONFIG_FILE" | grep -q '^interval=30$' \
  || fail 'memory block should poll at 30s interval'
grep -A2 '^\[bluetooth\]$' "$CONFIG_FILE" | grep -q '^interval=persist$' \
  || fail 'bluetooth block should use persist mode'
grep -A2 '^\[battery\]$' "$CONFIG_FILE" | grep -q '^interval=60$' \
  || fail 'battery block should poll at 60s interval'
grep -A2 '^\[ethernet\]$' "$CONFIG_FILE" | grep -q '^interval=persist$' \
  || fail 'ethernet block should use persist mode'
grep -A2 '^\[wifi\]$' "$CONFIG_FILE" | grep -q '^interval=persist$' \
  || fail 'wifi block should use persist mode'
grep -A2 '^\[activitywatch\]$' "$CONFIG_FILE" | grep -q '^interval=persist$' \
  || fail 'activitywatch block should use persist mode'
grep -A2 '^\[warp\]$' "$CONFIG_FILE" | grep -q '^interval=persist$' \
  || fail 'warp block should use persist mode'

printf 'Checking focus detection path avoids extra xdotool lookups...\n'
! grep -Fq "xdotool getwindowname \"\$wid\"" "$REPO_DIR/scripts/lib/common.sh" \
  || fail 'focus detection should not call xdotool getwindowname in hot path'

printf 'Checking ActivityWatch persist strategy avoids /proc event storm...\n'
! grep -Fq 'inotifywait -m -q -e create -e delete /proc' "$I3BLOCKS_DIR/activitywatch_status.sh" \
  || fail 'activitywatch persist mode should avoid noisy /proc inotify stream'

printf 'Checking GPU/WARP dedupe guards exist...\n'
grep -Fq 'emit_if_changed()' "$I3BLOCKS_DIR/gpu_monitor.sh" \
  || fail 'gpu monitor should dedupe repeated identical samples'
grep -Fq 'emit_if_changed()' "$I3BLOCKS_DIR/warp_status.sh" \
  || fail 'warp status should dedupe repeated identical states'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/bluetooth.sh" \
  || fail 'bluetooth script should use shared persist helper'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/wifi_monitor.sh" \
  || fail 'wifi script should use shared persist helper'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/ethernet.sh" \
  || fail 'ethernet script should use shared persist helper'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/activitywatch_status.sh" \
  || fail 'activitywatch script should use shared persist helper'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/gpu_monitor.sh" \
  || fail 'gpu script should use shared persist helper'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/warp_status.sh" \
  || fail 'warp script should use shared persist helper'
grep -Fq 'i3blocks_update_if_changed_key "bluetooth_state"' "$I3BLOCKS_DIR/bluetooth.sh" \
  || fail 'bluetooth script should dedupe unchanged state'
grep -Fq 'i3blocks_update_if_changed_key "wifi_output"' "$I3BLOCKS_DIR/wifi_monitor.sh" \
  || fail 'wifi script should dedupe unchanged output'
grep -Fq 'i3blocks_update_if_changed_key "ethernet_output"' "$I3BLOCKS_DIR/ethernet.sh" \
  || fail 'ethernet script should dedupe unchanged output'
grep -Fq 'i3blocks_update_if_changed_key "activitywatch_state"' "$I3BLOCKS_DIR/activitywatch_status.sh" \
  || fail 'activitywatch script should dedupe unchanged state'

printf 'Checking bluetooth block behavior and fork count...\n'
bluetooth_output=$(PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/bluetooth.sh")
assert_equals ' Test Headphones' "$(printf '%s\n' "$bluetooth_output" | sed -n '1p')" \
  'bluetooth script should show connected alias'
assert_le "$(count_execs "$I3BLOCKS_DIR/bluetooth.sh")" 2 \
  'bluetooth script should stay at one external helper plus bash'

printf 'Checking ActivityWatch block behavior and fork count...\n'
activitywatch_output=$(PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/activitywatch_status.sh")
assert_equals 'AW off' "$(printf '%s\n' "$activitywatch_output" | sed -n '1p')" \
  'activitywatch script should show AW off when not running'
assert_le "$(count_execs "$I3BLOCKS_DIR/activitywatch_status.sh")" 1 \
  'activitywatch script should avoid pacman/pgrep hot-path forks'

"$BIN_DIR/aw-qt" 60 >/dev/null 2>&1 &
AW_PID=$!
activitywatch_running_output=$(PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/activitywatch_status.sh")
assert_equals 'AW on' "$(printf '%s\n' "$activitywatch_running_output" | sed -n '1p')" \
  'activitywatch script should detect running aw-qt process'

printf 'Checking Wi-Fi block behavior and fork count...\n'
wifi_connected_output=$(PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/wifi_monitor.sh")
assert_equals '    TestWifi (-53 dBm) 192.168.1.44' \
  "$wifi_connected_output" \
  'wifi script should show ssid, signal, and IP when connected'
assert_le "$(count_execs "$I3BLOCKS_DIR/wifi_monitor.sh")" 4 \
  'wifi script should stay within bash plus iw/iw/ip exec budget'

wifi_disconnected_output=$(WIFI_CONNECTED=0 PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/wifi_monitor.sh")
assert_equals '    down' "$wifi_disconnected_output" \
  'wifi script should show down when the interface is not connected'

wifi_missing_output=$(WIFI_HAS_INTERFACE=0 PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/wifi_monitor.sh") || true
assert_equals '    down' "$wifi_missing_output" \
  'wifi script should show down when no Wi-Fi interface exists'

printf 'Checking WARP block behavior and fork count...\n'
warp_connected_output=$(WARP_STATUS=Connected PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/warp_status.sh")
assert_equals '🔒 !!! WARP CONNECTED !!!' "$(printf '%s\n' "$warp_connected_output" | sed -n '1p')" \
  'warp script should show the connected warning when WARP is enabled'
assert_equals '#FFFF00' "$(printf '%s\n' "$warp_connected_output" | sed -n '3p')" \
  'warp script should show yellow when WARP is connected'
assert_le "$(count_execs "$I3BLOCKS_DIR/warp_status.sh")" 2 \
  'warp script should stay at one external helper plus bash'

warp_disconnected_output=$(WARP_STATUS=Disconnected PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/warp_status.sh")
assert_equals 'WARP disconnected' "$(printf '%s\n' "$warp_disconnected_output" | sed -n '1p')" \
  'warp script should show the disconnected state'

warp_unknown_output=$(WARP_STATUS=Unknown PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/warp_status.sh")
assert_equals '⚠️ ! WARP unknown !' "$(printf '%s\n' "$warp_unknown_output" | sed -n '1p')" \
  'warp script should show the unknown state when status parsing fails'

printf 'Checking disk block behavior and fork count...\n'
disk_output=$(PATH="$BIN_DIR:$PATH" bash "$I3BLOCKS_DIR/disk.sh")
assert_equals '  15G/100G' "$disk_output" \
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

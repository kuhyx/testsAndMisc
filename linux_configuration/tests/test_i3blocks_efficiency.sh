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
grep -A2 '^\[ethernet\]$' "$CONFIG_FILE" | grep -q '^interval=persist$' \
  || fail 'ethernet block should use persist mode'
grep -A2 '^\[claude_usage\]$' "$CONFIG_FILE" | grep -q '^interval=60$' \
  || fail 'claude_usage block should poll at 60s interval'
grep -q '^command=~/.config/i3blocks/claude_usage.sh$' "$CONFIG_FILE" \
  || fail 'claude_usage block should call claude_usage.sh'

# Blocks for hardware/software absent from this machine were removed; make sure
# they do not silently return. Each rendered permanently-dead text in the bar.
for removed_block in bluetooth battery wifi activitywatch warp network_monitor; do
  if grep -q "^\[${removed_block}\]$" "$CONFIG_FILE"; then
    fail "removed block [${removed_block}] should not be in the config"
  fi
done

printf 'Checking status icons avoid Font Awesome private-use codepoints...\n'
# The fonts named in the i3 bar's pango string are not installed, so private-use
# codepoints (U+E000-U+F8FF) fall through to whatever font claims them - which
# rendered the ethernet icon as a star and the wifi icon as Cyrillic. Plain
# Unicode/emoji resolve consistently instead.
for icon_script in "$I3BLOCKS_DIR"/*.sh; do
  if grep -qP '[\x{E000}-\x{F8FF}]|\\u[eEfF][0-9a-fA-F]{3}' "$icon_script"; then
    fail "$(basename "$icon_script") should not use private-use-area icon codepoints"
  fi
done

printf 'Checking focus detection path avoids extra xdotool lookups...\n'
! grep -Fq "xdotool getwindowname \"\$wid\"" "$REPO_DIR/scripts/lib/common.sh" \
  || fail 'focus detection should not call xdotool getwindowname in hot path'

printf 'Checking GPU dedupe guards exist...\n'
grep -Fq 'emit_if_changed()' "$I3BLOCKS_DIR/gpu_monitor.sh" \
  || fail 'gpu monitor should dedupe repeated identical samples'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/ethernet.sh" \
  || fail 'ethernet script should use shared persist helper'
grep -Fq "source \"\$SCRIPT_DIR/persist_common.sh\"" "$I3BLOCKS_DIR/gpu_monitor.sh" \
  || fail 'gpu script should use shared persist helper'
grep -Fq 'i3blocks_update_if_changed_key "ethernet_output"' "$I3BLOCKS_DIR/ethernet.sh" \
  || fail 'ethernet script should dedupe unchanged output'

printf 'Checking ethernet picks a physical NIC over virtual bridges...\n'
# Regression: the old loop returned the first non-loopback interface, which on a
# machine with docker installed is a `br-*` bridge (always "down", and sorted
# before enp*/eth*), so the bar reported "down" on a live wired connection.
grep -Fq 'iface_path}/device' "$I3BLOCKS_DIR/ethernet.sh" \
  || fail 'ethernet script should require a real device to skip virtual interfaces'

printf 'Checking Claude usage block behavior and fork count...\n'
# claude_usage.sh parses its cache with jq and degrades to "no data" when jq is
# missing. That is the right runtime behaviour, but it would make every
# assertion below fail with a misleading message about percentages, so name the
# real cause instead of letting a missing tool look like a logic bug.
# Probe by running jq, not with `command -v`: a jq that exists but cannot
# execute produces exactly the same "no data" output as one that is absent.
printf '{}' | jq -e . >/dev/null 2>&1 \
  || fail 'a working jq is required for the claude_usage tests (pacman -S jq)'
CLAUDE_STATE_DIR="$TMP_DIR/limit-state"
mkdir -p "$CLAUDE_STATE_DIR"
claude_now=1786366861

write_claude_state() {
  printf '{"five_hour_pct":%s,"five_hour_resets_at":%s,"seven_day_pct":%s,"seven_day_resets_at":%s,"updated_at":%s}\n' \
    "$1" "$2" "$3" "$4" "$5" >"$CLAUDE_STATE_DIR/state.json"
}

run_claude_usage() {
  LIMIT_STATE_DIR="$CLAUDE_STATE_DIR" NOW_EPOCH="$claude_now" \
    bash "$I3BLOCKS_DIR/claude_usage.sh"
}

# Percentages arrive as floats (e.g. 55.00000000000001) and must be truncated.
write_claude_state 34 "$((claude_now + 3600))" 55.00000000000001 "$((claude_now + 99999))" "$claude_now"
claude_output=$(run_claude_usage)
assert_equals '🤖 5h 34% · 7d 55%' "$(printf '%s\n' "$claude_output" | sed -n '1p')" \
  'claude usage should show both windows as whole percentages'
assert_equals '#50FA7B' "$(printf '%s\n' "$claude_output" | sed -n '3p')" \
  'claude usage should be green well below the limit'

write_claude_state 70 "$((claude_now + 3600))" 12 "$((claude_now + 99999))" "$claude_now"
assert_equals '#F1FA8C' "$(run_claude_usage | sed -n '3p')" \
  'claude usage should warn when a window passes 60%'

write_claude_state 91 "$((claude_now + 3600))" 12 "$((claude_now + 99999))" "$claude_now"
assert_equals '#FF5555' "$(run_claude_usage | sed -n '3p')" \
  'claude usage should go critical when a window passes 85%'

# The writer only runs while a Claude session is open, so old data must be
# labelled rather than presented as the current figure.
write_claude_state 34 "$((claude_now + 3600))" 55 "$((claude_now + 99999))" "$((claude_now - 5000))"
assert_equals '🤖 5h 34% · 7d 55% (stale)' "$(run_claude_usage | sed -n '1p')" \
  'claude usage should mark stale cache data'

# A window whose reset time has passed has rolled over: its cached percentage is
# meaningless, so it must read as unknown rather than a misleading value.
write_claude_state 99 "$((claude_now - 10))" 55 "$((claude_now + 99999))" "$claude_now"
assert_equals '🤖 5h ?% · 7d 55%' "$(run_claude_usage | sed -n '1p')" \
  'claude usage should not report a rolled-over window as current'

write_claude_state 34 "$((claude_now + 3600))" 55 null "$claude_now"
assert_equals '🤖 5h 34% · 7d 55%' "$(run_claude_usage | sed -n '1p')" \
  'claude usage should tolerate a null seven_day reset time'

printf 'not json\n' >"$CLAUDE_STATE_DIR/state.json"
assert_equals '🤖 no data' "$(run_claude_usage | sed -n '1p')" \
  'claude usage should degrade gracefully on unparsable cache data'

claude_missing_output=$(LIMIT_STATE_DIR="$TMP_DIR/no-such-dir" NOW_EPOCH="$claude_now" \
  bash "$I3BLOCKS_DIR/claude_usage.sh")
assert_equals '🤖 no data' "$(printf '%s\n' "$claude_missing_output" | sed -n '1p')" \
  'claude usage should degrade gracefully when the cache directory is absent'

write_claude_state 34 "$((claude_now + 3600))" 55 "$((claude_now + 99999))" "$claude_now"
assert_le "$(LIMIT_STATE_DIR="$CLAUDE_STATE_DIR" NOW_EPOCH="$claude_now" \
  count_execs "$I3BLOCKS_DIR/claude_usage.sh")" 3 \
  'claude usage should stay within bash plus jq'

# The real cache holds one file per project (~170 on this machine), so the
# fork budget has to be measured against a populated directory. Measuring it
# against a single-file dir hid a `stat` call sitting inside the scan loop.
for filler in $(seq 1 200); do
  cp "$CLAUDE_STATE_DIR/state.json" "$CLAUDE_STATE_DIR/filler-$filler.json"
done
assert_le "$(LIMIT_STATE_DIR="$CLAUDE_STATE_DIR" NOW_EPOCH="$claude_now" \
  count_execs "$I3BLOCKS_DIR/claude_usage.sh")" 3 \
  'claude usage fork count must not scale with the number of cached projects'
rm -f "$CLAUDE_STATE_DIR"/filler-*.json

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

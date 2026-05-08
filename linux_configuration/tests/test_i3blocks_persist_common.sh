#!/bin/bash
# Regression tests for i3blocks persist_common helper functions.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
HELPER="$REPO_DIR/i3-configuration/i3blocks/persist_common.sh"
TMP_DIR=$(mktemp -d)

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# shellcheck source=linux_configuration/i3-configuration/i3blocks/persist_common.sh
source "$HELPER"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_eq() {
  local expected=$1
  local actual=$2
  local context=$3
  if [[ "$expected" != "$actual" ]]; then
    fail "$context (expected '$expected', actual '$actual')"
  fi
}

count_execs() {
  local script_path=$1
  local log_file=$2
  strace -f -o "$log_file" -e trace=execve bash "$script_path" >/dev/null 2>&1
  grep -c 'execve(' "$log_file"
}

printf 'Checking interval gating allows first emit per key...\n'
I3BLOCKS_LAST_TS=()
I3BLOCKS_TEST_NOW_TS=100
i3blocks_should_emit_by_interval_key "wifi" 5 || fail 'first interval check should allow emit'
assert_eq '100' "${I3BLOCKS_LAST_TS[wifi]}" 'first emit should store current timestamp'

printf 'Checking interval gating blocks too-soon second emit...\n'
I3BLOCKS_TEST_NOW_TS=102
if i3blocks_should_emit_by_interval_key "wifi" 5; then
  fail 'second interval check should block when interval has not elapsed'
fi
assert_eq '100' "${I3BLOCKS_LAST_TS[wifi]}" 'blocked emit must not overwrite timestamp'

printf 'Checking repeated blocked emits never mutate timestamp...\n'
for _ in {1..200}; do
  if i3blocks_should_emit_by_interval_key "wifi" 5; then
    fail 'repeated blocked interval checks must remain blocked'
  fi
done
assert_eq '100' "${I3BLOCKS_LAST_TS[wifi]}" 'repeated blocked checks must preserve original timestamp'

printf 'Checking interval gating allows later emit...\n'
I3BLOCKS_TEST_NOW_TS=106
i3blocks_should_emit_by_interval_key "wifi" 5 || fail 'emit should pass after interval elapsed'
assert_eq '106' "${I3BLOCKS_LAST_TS[wifi]}" 'allowed emit should update timestamp'

printf 'Checking interval gating is key-isolated...\n'
I3BLOCKS_TEST_NOW_TS=103
i3blocks_should_emit_by_interval_key "ethernet" 5 || fail 'new key should allow first emit independently'
assert_eq '103' "${I3BLOCKS_LAST_TS[ethernet]}" 'independent key should store its own timestamp'

unset I3BLOCKS_TEST_NOW_TS

printf 'Checking changed-state helper allows first state...\n'
I3BLOCKS_LAST_STATE=()
i3blocks_update_if_changed_key "wifi" "connected" || fail 'first state should be treated as changed'
assert_eq 'connected' "${I3BLOCKS_LAST_STATE[wifi]}" 'first changed state should be stored'

printf 'Checking changed-state helper blocks identical state...\n'
if i3blocks_update_if_changed_key "wifi" "connected"; then
  fail 'identical state should be treated as unchanged'
fi

printf 'Checking changed-state helper allows new state...\n'
i3blocks_update_if_changed_key "wifi" "disconnected" || fail 'different state should be treated as changed'
assert_eq 'disconnected' "${I3BLOCKS_LAST_STATE[wifi]}" 'new state should replace old state'

printf 'Checking empty string first state is treated as changed...\n'
I3BLOCKS_LAST_STATE=()
i3blocks_update_if_changed_key "warp" "" || fail 'first empty state should be treated as changed'
if i3blocks_update_if_changed_key "warp" ""; then
  fail 'second empty state should be treated as unchanged'
fi

printf 'Checking changed-state helper is key-isolated...\n'
i3blocks_update_if_changed_key "bluetooth" "on" || fail 'different key should track independently'
assert_eq 'on' "${I3BLOCKS_LAST_STATE[bluetooth]}" 'second key should store independent state'
assert_eq '' "${I3BLOCKS_LAST_STATE[warp]}" 'first key state should remain unchanged'

printf 'Checking interleaved multi-key updates remain isolated...\n'
I3BLOCKS_LAST_TS=()
I3BLOCKS_LAST_STATE=()
export I3BLOCKS_TEST_NOW_TS
for i in {1..50}; do
  I3BLOCKS_TEST_NOW_TS=$((1000 + i))
  i3blocks_should_emit_by_interval_key "wifi" 0 || fail 'wifi interleaved emit should pass'
  i3blocks_update_if_changed_key "wifi_state" "wifi-$((i % 3))" || true

  I3BLOCKS_TEST_NOW_TS=$((2000 + i))
  i3blocks_should_emit_by_interval_key "wifi_monitor" 0 || fail 'wifi_monitor interleaved emit should pass'
  i3blocks_update_if_changed_key "wifi_monitor_state" "monitor-$((i % 4))" || true

  I3BLOCKS_TEST_NOW_TS=$((3000 + i))
  i3blocks_should_emit_by_interval_key "ethernet" 0 || fail 'ethernet interleaved emit should pass'
  i3blocks_update_if_changed_key "ethernet_state" "eth-$((i % 2))" || true
done
assert_eq '1050' "${I3BLOCKS_LAST_TS[wifi]}" 'wifi key should retain its own timestamp series'
assert_eq '2050' "${I3BLOCKS_LAST_TS[wifi_monitor]}" 'wifi_monitor key should retain its own timestamp series'
assert_eq '3050' "${I3BLOCKS_LAST_TS[ethernet]}" 'ethernet key should retain its own timestamp series'
assert_eq 'wifi-2' "${I3BLOCKS_LAST_STATE[wifi_state]}" 'wifi_state should keep independent final state'
assert_eq 'monitor-2' "${I3BLOCKS_LAST_STATE[wifi_monitor_state]}" 'wifi_monitor_state should keep independent final state'
assert_eq 'eth-0' "${I3BLOCKS_LAST_STATE[ethernet_state]}" 'ethernet_state should keep independent final state'
unset I3BLOCKS_TEST_NOW_TS

printf 'Checking helper hot path stays fork-free under load...\n'
fork_probe="$TMP_DIR/persist_common_fork_probe.sh"
cat >"$fork_probe" <<EOF
#!/bin/bash
set -euo pipefail

# shellcheck source=linux_configuration/i3-configuration/i3blocks/persist_common.sh
source "$HELPER"

I3BLOCKS_LAST_TS=()
I3BLOCKS_LAST_STATE=()

for i in {1..2000}; do
  i3blocks_should_emit_by_interval_key "wifi" 0
  i3blocks_update_if_changed_key "wifi_state" "state-\$((i % 3))"
done
EOF
chmod +x "$fork_probe"

exec_count=$(count_execs "$fork_probe" "$TMP_DIR/fork_probe.trace")
assert_eq '1' "$exec_count" 'persist helper hot path should not fork external commands'

printf 'persist_common helper regression tests passed.\n'

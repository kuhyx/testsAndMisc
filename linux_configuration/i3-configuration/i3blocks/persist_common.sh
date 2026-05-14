#!/bin/bash
# Shared helpers for persist-mode i3blocks scripts.

set -u

declare -gA I3BLOCKS_LAST_TS=()
declare -gA I3BLOCKS_LAST_STATE=()

# Return current epoch seconds using bash builtin time formatting.
i3blocks_now_ts() {
  if [[ -n ${I3BLOCKS_TEST_NOW_TS:-} ]]; then
    printf '%s\n' "$I3BLOCKS_TEST_NOW_TS"
    return 0
  fi
  printf '%(%s)T' -1
}

# Return 0 when enough time elapsed since last emit timestamp for key.
# Usage: if i3blocks_should_emit_by_interval_key "wifi" 2; then ...
i3blocks_should_emit_by_interval_key() {
  local key=$1
  local min_interval_s=$2
  local now last

  now=$(i3blocks_now_ts)
  last=${I3BLOCKS_LAST_TS[$key]:-0}

  if (( now - last < min_interval_s )); then
    return 1
  fi

  I3BLOCKS_LAST_TS[$key]=$now
  return 0
}

# Return 0 when new state differs from current value for key, then update.
# Usage: if i3blocks_update_if_changed_key "wifi_output" "$line"; then emit; fi
i3blocks_update_if_changed_key() {
  local key=$1
  local new_state=$2
  local current_state

  if [[ -v I3BLOCKS_LAST_STATE[$key] ]]; then
    current_state=${I3BLOCKS_LAST_STATE[$key]}
  else
    current_state=''
  fi

  if [[ -v I3BLOCKS_LAST_STATE[$key] && $current_state == "$new_state" ]]; then
    return 1
  fi

  I3BLOCKS_LAST_STATE[$key]=$new_state
  return 0
}

# Wait for a number of seconds without forking an external `sleep` process.
# Uses bash builtin read timeout. Set I3BLOCKS_TEST_SKIP_WAIT=1 to bypass in tests.
i3blocks_wait_seconds() {
  local timeout_s=$1

  if [[ ${I3BLOCKS_TEST_SKIP_WAIT:-0} -eq 1 ]]; then
    return 0
  fi

  IFS= read -r -t "$timeout_s" || true
}

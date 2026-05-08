#!/bin/bash
# i3blocks Wi-Fi indicator with a small, bounded helper budget.

set -euo pipefail

SCRIPT_DIR=${BASH_SOURCE[0]%/*}
[[ $SCRIPT_DIR == "${BASH_SOURCE[0]}" ]] && SCRIPT_DIR='.'
# shellcheck source=linux_configuration/i3-configuration/i3blocks/persist_common.sh
source "$SCRIPT_DIR/persist_common.sh"

find_wifi_interface() {
  local line
  while IFS= read -r line; do
    case $line in
      *'Interface '*)
        printf '%s\n' "${line##*Interface }"
        return 0
        ;;
    esac
  done < <(iw dev 2> /dev/null)
  return 1
}

emit() {
  local wifi_interface ssid signal ip_address line fields i output_line

  wifi_interface=$(find_wifi_interface) || {
    output_line='    down'
    if i3blocks_update_if_changed_key "wifi_output" "$output_line"; then
      echo "$output_line"
    fi
    return 0
  }

  ssid=''
  signal=''
  while IFS= read -r line; do
    case $line in
      'SSID: '*)
        ssid=${line#SSID: }
        ;;
      'signal: '*)
        signal=${line#signal: }
        signal=${signal% dBm}
        ;;
      'Not connected.'*)
        ssid=''
        ;;
    esac
  done < <(iw dev "$wifi_interface" link 2> /dev/null)

  if [[ -z $ssid ]]; then
    output_line='    down'
    if i3blocks_update_if_changed_key "wifi_output" "$output_line"; then
      echo "$output_line"
    fi
    return 0
  fi

  ip_address=''
  while IFS= read -r line; do
    [[ $line == *' inet '* ]] || continue
    read -r -a fields <<< "$line"
    for ((i = 0; i < ${#fields[@]}; i++)); do
      if [[ ${fields[i]} == inet && $((i + 1)) -lt ${#fields[@]} ]]; then
        ip_address=${fields[i + 1]%%/*}
        break 2
      fi
    done
  done < <(ip -o -4 addr show dev "$wifi_interface" scope global 2> /dev/null)

  if [[ -n $ip_address ]]; then
    output_line="    $ssid ($signal dBm) $ip_address"
  else
    output_line="    $ssid ($signal dBm)"
  fi

  if i3blocks_update_if_changed_key "wifi_output" "$output_line"; then
    echo "$output_line"
  fi
}

is_persist_mode() {
  [[ ${BLOCK_INTERVAL:-} == "persist" ]]
}

emit_throttled() {
  if ! i3blocks_should_emit_by_interval_key "wifi_emit" "$EMIT_MIN_INTERVAL_S"; then
    return 0
  fi
  emit
}

EMIT_MIN_INTERVAL_S=2

emit

if is_persist_mode; then
  ip monitor link address route 2> /dev/null |
    while read -r line; do
      [[ $line == *"wlan"* || $line == *"wl"* || $line == *"inet "* ]] || continue
      emit_throttled
    done
fi

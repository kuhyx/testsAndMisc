#!/bin/bash
# i3blocks bluetooth indicator.

set -euo pipefail

SCRIPT_DIR=${BASH_SOURCE[0]%/*}
[[ $SCRIPT_DIR == "${BASH_SOURCE[0]}" ]] && SCRIPT_DIR='.'
# shellcheck source=linux_configuration/i3-configuration/i3blocks/persist_common.sh
source "$SCRIPT_DIR/persist_common.sh"

get_bluetooth_info() {
  local info
  info=$(bluetoothctl info 2> /dev/null) || info=''
  printf '%s\n' "$info"
}

emit() {
  local bluetooth_info connected device line state_key
  bluetooth_info=$(get_bluetooth_info)

  connected='no'
  device=''
  while IFS= read -r line; do
    case $line in
      *'Connected: yes')
        connected='yes'
        ;;
      *'Alias: '*)
        device=${line#*Alias: }
        ;;
    esac
  done <<< "$bluetooth_info"

  state_key="$connected|$device"
  if ! i3blocks_update_if_changed_key "bluetooth_state" "$state_key"; then
    return 0
  fi

  if [[ $connected == yes && -n $device ]]; then
    echo " $device"
    echo
    echo "#50FA7B"
  else
    echo " Disconnected"
  fi
}

is_persist_mode() {
  [[ ${BLOCK_INTERVAL:-} == "persist" ]]
}

emit_throttled() {
  if ! i3blocks_should_emit_by_interval_key "bluetooth_emit" "$EMIT_MIN_INTERVAL_S"; then
    return 0
  fi
  emit
}

EMIT_MIN_INTERVAL_S=2

emit

if is_persist_mode; then
  # React to BlueZ D-Bus signals instead of polling.
  if command -v dbus-monitor > /dev/null 2>&1; then
    dbus-monitor --system "type='signal',sender='org.bluez'" 2> /dev/null |
      while read -r line; do
        [[ $line == *"PropertiesChanged"* ]] || continue
        emit_throttled
      done
  fi
fi

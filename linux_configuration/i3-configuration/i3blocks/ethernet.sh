#!/bin/bash
# i3blocks ethernet indicator with one external helper at most.

set -euo pipefail

SCRIPT_DIR=${BASH_SOURCE[0]%/*}
[[ $SCRIPT_DIR == "${BASH_SOURCE[0]}" ]] && SCRIPT_DIR='.'
# shellcheck source=linux_configuration/i3-configuration/i3blocks/persist_common.sh
source "$SCRIPT_DIR/persist_common.sh"

find_ethernet_interface() {
  local iface_path iface
  for iface_path in /sys/class/net/*; do
    iface=${iface_path##*/}
    [[ $iface == lo ]] && continue
    [[ -d ${iface_path}/wireless ]] && continue
    [[ -r ${iface_path}/operstate ]] || continue
    printf '%s\n' "$iface"
    return 0
  done
  return 1
}

emit() {
  local iface state addr_output output_line
  iface=$(find_ethernet_interface) || {
    output_line='  down'
    if i3blocks_update_if_changed_key "ethernet_output" "$output_line"; then
      printf '%s\n' "$output_line"
    fi
    return 0
  }

  read -r state < "/sys/class/net/${iface}/operstate"
  if [[ $state != up ]]; then
    output_line='  down'
    if i3blocks_update_if_changed_key "ethernet_output" "$output_line"; then
      printf '%s\n' "$output_line"
    fi
    return 0
  fi

  addr_output=$(ip -o -4 addr show dev "$iface" scope global 2> /dev/null) || addr_output=''
  if [[ $addr_output =~ ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+) ]]; then
    output_line="    ${BASH_REMATCH[1]}"
  else
    output_line='  down'
  fi

  if i3blocks_update_if_changed_key "ethernet_output" "$output_line"; then
    printf '%s\n' "$output_line"
  fi
}

is_persist_mode() {
  [[ ${BLOCK_INTERVAL:-} == "persist" ]]
}

emit_throttled() {
  if ! i3blocks_should_emit_by_interval_key "ethernet_emit" "$EMIT_MIN_INTERVAL_S"; then
    return 0
  fi
  emit
}

EMIT_MIN_INTERVAL_S=2

emit

if is_persist_mode; then
  ip monitor link address route 2> /dev/null |
    while read -r line; do
      [[ $line == *"eth"* || $line == *"en"* || $line == *"inet "* ]] || continue
      emit_throttled
    done
fi

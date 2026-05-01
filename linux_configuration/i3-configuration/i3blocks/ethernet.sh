#!/bin/bash
# i3blocks ethernet indicator with one external helper at most.

set -euo pipefail

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

iface=$(find_ethernet_interface) || {
  printf '  down\n'
  exit 0
}

read -r state < "/sys/class/net/${iface}/operstate"
if [[ $state != up ]]; then
  printf '  down\n'
  exit 0
fi

addr_output=$(ip -o -4 addr show dev "$iface" scope global 2> /dev/null) || addr_output=''
if [[ $addr_output =~ ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+) ]]; then
  printf '    %s\n' "${BASH_REMATCH[1]}"
else
  printf '  down\n'
fi

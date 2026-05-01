#!/bin/bash
# i3blocks Wi-Fi indicator with a small, bounded helper budget.

set -euo pipefail

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

wifi_interface=$(find_wifi_interface) || {
  echo "    down"
  exit 0
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
  echo "    down"
  exit 0
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
  echo "    $ssid ($signal dBm) $ip_address"
else
  echo "    $ssid ($signal dBm)"
fi

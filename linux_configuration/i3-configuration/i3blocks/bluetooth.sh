#!/bin/bash
# i3blocks bluetooth indicator.

set -euo pipefail

bluetooth_info=$(bluetoothctl info 2> /dev/null) || bluetooth_info=''

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

if [[ $connected == yes && -n $device ]]; then
  echo " $device"
  echo
  echo "#50FA7B"
else
  echo " Disconnected"
fi

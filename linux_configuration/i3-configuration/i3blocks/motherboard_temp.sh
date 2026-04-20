#!/bin/bash
# i3blocks motherboard-temperature indicator, zero-fork per invocation.
#
# Reads /sys/class/hwmon directly instead of forking `sensors | awk | tr`.
# Prefers Super-I/O chips (nct*, it*, f71*) which expose the true board
# sensor; falls back to the first non-CPU/GPU/NIC hwmon with a temp1_input.

set -u

hwmon=''
for d in /sys/class/hwmon/hwmon*/; do
  [[ -r ${d}name ]] || continue
  read -r n < "${d}name"
  case $n in
    nct* | it87* | it8* | f71*)
      hwmon=$d
      break
      ;;
  esac
done
if [[ -z $hwmon ]]; then
  for d in /sys/class/hwmon/hwmon*/; do
    [[ -r ${d}name && -r ${d}temp1_input ]] || continue
    read -r n < "${d}name"
    case $n in
      k10temp | coretemp | amdgpu | nouveau | nvme | r8169* | iwlwifi*) continue ;;
      *)
        hwmon=$d
        break
        ;;
    esac
  done
fi

if [[ -z $hwmon || ! -r ${hwmon}temp1_input ]]; then
  printf '  MB: N/A\n\n#FF5555\n'
  exit 0
fi

read -r milli < "${hwmon}temp1_input"
temp=$((milli / 1000))

if ((temp < 50)); then
  color='#50FA7B'
elif ((temp < 70)); then
  color='#F1FA8C'
else
  color='#FF5555'
fi

printf '  %s°C\n\n%s\n' "$temp" "$color"

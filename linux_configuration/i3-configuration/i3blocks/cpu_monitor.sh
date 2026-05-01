#!/bin/bash
# i3blocks CPU monitor, zero-fork per invocation.
#
# Reads /proc/loadavg and /sys/class/hwmon/*/temp*_input directly instead
# of forking `sensors | awk | tr` and `echo | bc`. Pure bash builtins.

set -u

# Locate AMD k10temp or Intel coretemp hwmon node.
hwmon=''
for d in /sys/class/hwmon/hwmon*/; do
  [[ -r ${d}name ]] || continue
  read -r n < "${d}name"
  case $n in
    k10temp | coretemp)
      hwmon=$d
      break
      ;;
  esac
done

temp='N/A'
temp_int=-1
if [[ -n $hwmon && -r ${hwmon}temp1_input ]]; then
  read -r milli < "${hwmon}temp1_input"
  temp_int=$((milli / 1000))
  temp=$temp_int
fi

load='N/A'
load_x100=0
if [[ -r /proc/loadavg ]]; then
  read -r one _ < /proc/loadavg
  load=$one
  # loadavg prints two decimals, e.g. "1.23" → 123, "0.05" → 5.
  load_digits=${one//./}
  load_digits=${load_digits##0}
  load_x100=$((10#${load_digits:-0}))
fi

color='#FFFFFF'
if ((temp_int >= 0)); then
  if ((temp_int < 65)); then
    color='#50FA7B'
  elif ((temp_int < 85)); then
    color='#F1FA8C'
  else
    color='#FF5555'
  fi
elif ((load_x100 > 0)); then
  if ((load_x100 < 100)); then
    color='#50FA7B'
  elif ((load_x100 < 200)); then
    color='#F1FA8C'
  else
    color='#FF5555'
  fi
fi

# Nerd Font glyph: microchip / CPU icon (U+F2DB).
printf '<span color="%s">\uf2db    %s°C, %s</span>\n' "$color" "$temp" "$load"

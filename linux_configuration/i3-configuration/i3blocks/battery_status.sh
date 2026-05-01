#!/bin/bash
# i3blocks battery indicator, zero-fork per invocation.
#
# Reads /sys/class/power_supply directly instead of forking `acpi | awk`.
# Uses only bash builtins (read, printf, arithmetic, parameter expansion).

set -u

# Nerd Font glyph: battery-full icon (U+F240).
ICON=$'\uf240'

bat=
for d in /sys/class/power_supply/BAT*/; do
  [[ -d $d ]] && {
    bat=$d
    break
  }
done

if [[ -z $bat ]]; then
  # Desktop with no battery — emit empty block so i3bar hides it.
  echo
  exit 0
fi

cap='N/A'
[[ -r ${bat}capacity ]] && read -r cap < "${bat}capacity"

status=''
[[ -r ${bat}status ]] && read -r status < "${bat}status"

# Compute time remaining from energy_now/power_now (µWh / µW → hours).
# Falls back to charge_now/current_now on batteries that expose charge instead.
time_str=''
num=0
den=0
if [[ -r ${bat}energy_now && -r ${bat}power_now ]]; then
  read -r num < "${bat}energy_now"
  read -r den < "${bat}power_now"
elif [[ -r ${bat}charge_now && -r ${bat}current_now ]]; then
  read -r num < "${bat}charge_now"
  read -r den < "${bat}current_now"
fi
if ((den > 0 && num > 0)); then
  total_min=$((num * 60 / den))
  printf -v time_str '%02d:%02d' "$((total_min / 60))" "$((total_min % 60))"
fi

color='#50FA7B'
if [[ $cap =~ ^[0-9]+$ ]]; then
  if ((cap < 15)); then
    color='#FF5555'
  elif ((cap < 35)); then
    color='#F1FA8C'
  fi
fi
[[ $status == Charging ]] && color='#8BE9FD'

printf -v body '%s %s%%' "$ICON" "$cap"
[[ -n $time_str ]] && body+=", $time_str"
[[ $status == Charging ]] && body+=', '
printf '<span color="%s">%s</span>\n' "$color" "$body"

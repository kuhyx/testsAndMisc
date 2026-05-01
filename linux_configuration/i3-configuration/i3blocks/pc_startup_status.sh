#!/bin/bash
# PC Startup Monitor status script for i3blocks.

set -euo pipefail

get_now_epoch() {
  if [[ -n ${NOW_EPOCH:-} ]]; then
    printf '%s\n' "$NOW_EPOCH"
  else
    printf '%(%s)T\n' -1
  fi
}

get_uptime_seconds() {
  local uptime_line
  if [[ -n ${UPTIME_SECONDS:-} ]]; then
    printf '%s\n' "$UPTIME_SECONDS"
    return 0
  fi

  read -r uptime_line _ < /proc/uptime || uptime_line='0'
  printf '%s\n' "${uptime_line%%.*}"
}

is_monitored_day() {
  local epoch=$1 day_of_week
  printf -v day_of_week '%(%u)T' "$epoch"
  case $day_of_week in
    1 | 5 | 6 | 7)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

hour_in_window() {
  local epoch=$1 hour
  printf -v hour '%(%H)T' "$epoch"
  ((10#$hour >= 5 && 10#$hour < 8))
}

was_booted_in_window_today() {
  local now_epoch=$1 boot_epoch now_day boot_day
  boot_epoch=$((now_epoch - $(get_uptime_seconds)))
  printf -v now_day '%(%Y-%m-%d)T' "$now_epoch"
  printf -v boot_day '%(%Y-%m-%d)T' "$boot_epoch"
  [[ $boot_day == "$now_day" ]] || return 1
  hour_in_window "$boot_epoch"
}

now_epoch=$(get_now_epoch)

if ! is_monitored_day "$now_epoch"; then
  echo "PC:skip"
  echo
  echo "#888888"
elif hour_in_window "$now_epoch"; then
  echo "PC:live"
  echo
  echo "#00FF00"
elif was_booted_in_window_today "$now_epoch"; then
  echo "PC:ok"
  echo
  echo "#00FF00"
else
  echo "PC:warn"
  echo
  echo "#FF0000"
fi

#!/bin/bash
# Shutdown countdown status script for i3blocks.

set -euo pipefail

SHUTDOWN_CONFIG=${SHUTDOWN_CONFIG:-/etc/shutdown-schedule.conf}

# Function to show error state in i3blocks and exit
show_error() {
  local message="$1"
  echo "⏻ $message"
  echo "⏻"
  echo "#FF79C6" # Pink/magenta for config errors
  exit 0
}

if [[ ! -f $SHUTDOWN_CONFIG ]]; then
  show_error "NO CONFIG"
fi

MON_WED_HOUR=''
THU_SUN_HOUR=''
morning_end_hour='5'
while IFS='=' read -r key value; do
  value=${value%%[[:space:]]*}
  case $key in
    MON_WED_HOUR)
      MON_WED_HOUR=$value
      ;;
    THU_SUN_HOUR)
      THU_SUN_HOUR=$value
      ;;
    MORNING_END_HOUR)
      morning_end_hour=$value
      ;;
  esac
done < "$SHUTDOWN_CONFIG"

if [[ -z $MON_WED_HOUR ]] || [[ -z $THU_SUN_HOUR ]]; then
  show_error "MISSING VARS"
fi

if ! [[ $MON_WED_HOUR =~ ^[0-9]+$ ]] || ! [[ $THU_SUN_HOUR =~ ^[0-9]+$ ]]; then
  show_error "INVALID HOURS"
fi

if ! [[ $morning_end_hour =~ ^[0-9]+$ ]]; then
  show_error "INVALID HOURS"
fi

get_now_epoch() {
  if [[ -n ${NOW_EPOCH:-} ]]; then
    printf '%s\n' "$NOW_EPOCH"
  else
    printf '%(%s)T\n' -1
  fi
}

now_epoch=$(get_now_epoch)
printf -v current_hour '%(%H)T' "$now_epoch"
printf -v current_minute '%(%M)T' "$now_epoch"
printf -v day_of_week '%(%u)T' "$now_epoch"

current_time_minutes=$((10#$current_hour * 60 + 10#$current_minute))
morning_end_minutes=$((10#$morning_end_hour * 60))

if [[ $day_of_week -ge 1 ]] && [[ $day_of_week -le 3 ]]; then
  shutdown_hour=$MON_WED_HOUR
else
  shutdown_hour=$THU_SUN_HOUR
fi

shutdown_time_minutes=$((shutdown_hour * 60))

if [[ $current_time_minutes -ge $shutdown_time_minutes ]] || [[ $current_time_minutes -le $morning_end_minutes ]]; then
  echo "⏻ SHUTDOWN"
  echo "⏻"
  echo "#FF5555"
  exit 0
fi

minutes_until_shutdown=$((shutdown_time_minutes - current_time_minutes))
hours=$((minutes_until_shutdown / 60))
minutes=$((minutes_until_shutdown % 60))

if [[ $hours -gt 0 ]]; then
  time_str="${hours}h ${minutes}m"
else
  time_str="${minutes}m"
fi

if [[ $minutes_until_shutdown -le 30 ]]; then
  color="#FF5555"
  icon="⏻"
elif [[ $minutes_until_shutdown -le 60 ]]; then
  color="#FFB86C"
  icon="⏻"
elif [[ $minutes_until_shutdown -le 120 ]]; then
  color="#F1FA8C"
  icon="⏻"
else
  color="#6272A4"
  icon="⏻"
fi

echo "$icon $time_str"
echo "$icon"
echo "$color"

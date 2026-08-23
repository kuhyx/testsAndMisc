#!/bin/bash
# Shutdown countdown status script for i3blocks.
# Shows the exact absolute time of the next enforced shutdown, or the
# overridden time if a shutdown-override-manager.sh window rescues it.

set -euo pipefail

SHUTDOWN_CONFIG=${SHUTDOWN_CONFIG:-/etc/shutdown-schedule.conf}
SKIP_DATES_FILE=${SKIP_DATES_FILE:-/etc/shutdown-skip-dates}
OVERRIDES_FILE=${OVERRIDES_FILE:-/etc/shutdown-schedule-overrides.conf}

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
printf -v today_date '%(%Y-%m-%d)T' "$now_epoch"
# Fork-free whole-line match against the skip-dates file (bash builtin read,
# no `grep` process spawned every tick). Equivalent to `grep -qxF`.
if [[ -r $SKIP_DATES_FILE ]]; then
  while IFS= read -r skip_date || [[ -n $skip_date ]]; do
    if [[ $skip_date == "$today_date" ]]; then
      exit 0
    fi
  done < "$SKIP_DATES_FILE"
fi

printf -v current_hour '%(%H)T' "$now_epoch"
printf -v current_minute '%(%M)T' "$now_epoch"
printf -v current_second '%(%S)T' "$now_epoch"
printf -v day_of_week '%(%u)T' "$now_epoch"

current_time_minutes=$((10#$current_hour * 60 + 10#$current_minute))
morning_end_minutes=$((10#$morning_end_hour * 60))
midnight_epoch=$((now_epoch - (10#$current_hour * 3600 + 10#$current_minute * 60 + 10#$current_second)))

if [[ $day_of_week -ge 1 ]] && [[ $day_of_week -le 3 ]]; then
  shutdown_hour=$MON_WED_HOUR
else
  shutdown_hour=$THU_SUN_HOUR
fi

shutdown_time_minutes=$((shutdown_hour * 60))
shutdown_epoch_today=$((midnight_epoch + shutdown_hour * 3600))

# Prints "start_epoch|end_epoch|reason" for the first registered override
# (shutdown-override-manager.sh) whose window covers the given epoch, empty
# otherwise. Builtin `read` only - no forks in this hot path.
find_override_covering() {
  local target_epoch=$1
  [[ -f $OVERRIDES_FILE ]] || return 1
  local start_epoch end_epoch _created reason
  while IFS='|' read -r start_epoch end_epoch _created reason; do
    [[ -n $start_epoch ]] || continue
    if [[ $target_epoch -ge $start_epoch ]] && [[ $target_epoch -le $end_epoch ]]; then
      printf '%s|%s|%s\n' "$start_epoch" "$end_epoch" "$reason"
      return 0
    fi
  done <"$OVERRIDES_FILE"
  return 1
}

format_hhmm() {
  printf '%(%H:%M)T' "$1"
}

# Case 1: an override is active right now - always takes priority, whether
# or not we are inside the normal blocked window.
if override_match=$(find_override_covering "$now_epoch"); then
  IFS='|' read -r _ override_end _ <<<"$override_match"
  echo "▶ $(format_hhmm "$override_end") (override)"
  echo "▶ $(format_hhmm "$override_end")"
  echo "#50FA7B"
  exit 0
fi

# Case 2: currently inside the normal blocked window with no rescuing
# override registered - shutdown is due now.
if [[ $current_time_minutes -ge $shutdown_time_minutes ]] || [[ $current_time_minutes -le $morning_end_minutes ]]; then
  echo "⏻ SHUTDOWN"
  echo "⏻"
  echo "#FF5555"
  exit 0
fi

# Case 3: normal usable time. Show the exact hour of the next shutdown,
# unless a registered override starts before it and extends past it - in
# which case show the rescued (overridden) time instead, proactively.
if override_match=$(find_override_covering "$shutdown_epoch_today"); then
  IFS='|' read -r _ override_end _ <<<"$override_match"
  echo "▶ $(format_hhmm "$override_end") (override)"
  echo "▶ $(format_hhmm "$override_end")"
  echo "#50FA7B"
  exit 0
fi

minutes_until_shutdown=$((shutdown_time_minutes - current_time_minutes))

if [[ $minutes_until_shutdown -le 30 ]]; then
  color="#FF5555"
elif [[ $minutes_until_shutdown -le 60 ]]; then
  color="#FFB86C"
elif [[ $minutes_until_shutdown -le 120 ]]; then
  color="#F1FA8C"
else
  color="#6272A4"
fi

echo "⏻ $(format_hhmm "$shutdown_epoch_today")"
echo "⏻"
echo "$color"

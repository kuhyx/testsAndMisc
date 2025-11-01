#!/bin/bash
# PC Startup Monitor status script for i3blocks
# Shows compact startup compliance status in the status bar

# Function to check if today is a monitored day
is_monitored_day() {
  local day_of_week
  day_of_week=$(date +%u)
  if [[ $day_of_week == "1" ]] || [[ $day_of_week == "5" ]] || [[ $day_of_week == "6" ]] || [[ $day_of_week == "7" ]]; then
    return 0
  else
    return 1
  fi
}

# Function to check if current time is in window
is_current_time_in_window() {
  local current_hour current_hour_num
  current_hour=$(date +%H)
  current_hour_num=$((10#$current_hour))
  if [[ $current_hour_num -ge 5 ]] && [[ $current_hour_num -lt 8 ]]; then
    return 0
  else
    return 1
  fi
}

# Function to check if PC was booted in window today
was_booted_in_window_today() {
  local today uptime_seconds boot_time boot_date
  today=$(date +%Y-%m-%d)
  uptime_seconds=$(awk '{print int($1)}' /proc/uptime 2> /dev/null || echo "0")
  boot_time=$(date -d "@$(($(date +%s) - uptime_seconds))" +"%Y-%m-%d %H:%M:%S")
  boot_date=$(echo "$boot_time" | cut -d' ' -f1)

  if [[ $boot_date != "$today" ]]; then
    return 1
  fi

  local boot_hour boot_hour_num
  boot_hour=$(echo "$boot_time" | cut -d' ' -f2 | cut -d':' -f1)
  boot_hour_num=$((10#$boot_hour))

  if [[ $boot_hour_num -ge 5 ]] && [[ $boot_hour_num -lt 8 ]]; then
    return 0
  else
    return 1
  fi
}

# Main logic
if ! is_monitored_day; then
  # Not a monitored day
  echo "PC:skip"
  echo
  echo "#888888" # Gray
elif is_current_time_in_window; then
  # Currently in the window - all good
  echo "PC:live"
  echo
  echo "#00FF00" # Green
elif was_booted_in_window_today; then
  # Was booted in window today - compliant
  echo "PC:ok"
  echo
  echo "#00FF00" # Green
else
  # Was NOT booted in window today - non-compliant
  echo "PC:warn"
  echo
  echo "#FF0000" # Red
fi

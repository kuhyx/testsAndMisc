#!/bin/bash
# Shutdown countdown status script for i3blocks
# Shows time remaining until the next shutdown window
# Reads shutdown times from shared config file written by setup_midnight_shutdown.sh

SHUTDOWN_CONFIG="/etc/shutdown-schedule.conf"

# Function to show error state in i3blocks and exit
show_error() {
  local message="$1"
  echo "⏻ $message"
  echo "⏻"
  echo "#FF79C6" # Pink/magenta for config errors
  exit 0
}

# Validate and load config file
if [[ ! -f $SHUTDOWN_CONFIG ]]; then
  show_error "NO CONFIG"
fi

# Source the config file to get MON_WED_HOUR and THU_SUN_HOUR
# shellcheck source=/dev/null
if ! source "$SHUTDOWN_CONFIG" 2> /dev/null; then
  show_error "BAD CONFIG"
fi

# Validate that required variables are set
if [[ -z ${MON_WED_HOUR:-} ]] || [[ -z ${THU_SUN_HOUR:-} ]]; then
  show_error "MISSING VARS"
fi

# Validate that values are numbers
if ! [[ $MON_WED_HOUR =~ ^[0-9]+$ ]] || ! [[ $THU_SUN_HOUR =~ ^[0-9]+$ ]]; then
  show_error "INVALID HOURS"
fi

# Get current time info
current_hour=$(date +%H)
current_minute=$(date +%M)
current_time_minutes=$((10#$current_hour * 60 + 10#$current_minute))
day_of_week=$(date +%u) # 1=Monday, 7=Sunday

# Determine shutdown hour based on day of week
if [[ $day_of_week -ge 1 ]] && [[ $day_of_week -le 3 ]]; then
  # Monday-Wednesday
  shutdown_hour=$MON_WED_HOUR
else
  # Thursday-Sunday
  shutdown_hour=$THU_SUN_HOUR
fi

shutdown_time_minutes=$((shutdown_hour * 60))

# Check if we're currently in the shutdown window (after shutdown time or before 05:00)
if [[ $current_time_minutes -ge $shutdown_time_minutes ]] || [[ $current_time_minutes -le 300 ]]; then
  # We're in shutdown window - show warning
  echo "⏻ SHUTDOWN"
  echo "⏻"
  echo "#FF5555"
  exit 0
fi

# Calculate minutes until shutdown
minutes_until_shutdown=$((shutdown_time_minutes - current_time_minutes))

# Convert to hours and minutes
hours=$((minutes_until_shutdown / 60))
minutes=$((minutes_until_shutdown % 60))

# Format output
if [[ $hours -gt 0 ]]; then
  time_str="${hours}h ${minutes}m"
else
  time_str="${minutes}m"
fi

# Color based on time remaining
if [[ $minutes_until_shutdown -le 30 ]]; then
  # Less than 30 min - red warning
  color="#FF5555"
  icon="⏻"
elif [[ $minutes_until_shutdown -le 60 ]]; then
  # Less than 1 hour - orange warning
  color="#FFB86C"
  icon="⏻"
elif [[ $minutes_until_shutdown -le 120 ]]; then
  # Less than 2 hours - yellow
  color="#F1FA8C"
  icon="⏻"
else
  # More than 2 hours - normal
  color="#6272A4"
  icon="⏻"
fi

# Output for i3blocks (full_text, short_text, color)
echo "$icon $time_str"
echo "$icon"
echo "$color"

#!/bin/bash
# Shutdown countdown status script for i3blocks
# Shows time remaining until the next shutdown window
# Dynamically reads shutdown times from the systemd check script

SHUTDOWN_CHECK_SCRIPT="/usr/local/bin/day-specific-shutdown-check.sh"

# Function to extract shutdown hour from the check script
# Parses lines like "if [[ $current_time_minutes -ge 1260 ]]" where 1260 = 21*60
get_shutdown_hours() {
	if [[ ! -f "$SHUTDOWN_CHECK_SCRIPT" ]]; then
		# Fallback defaults if script not found
		echo "21 22"
		return
	fi

	# Extract the minute thresholds from the script (e.g., 1260 for 21:00, 1320 for 22:00)
	# The script checks: if [[ $current_time_minutes -ge XXXX ]]
	# Get unique values - first is Mon-Wed (1260=21:00), second is Thu-Sun (1320=22:00)
	local thresholds
	thresholds=$(grep -oP 'current_time_minutes -ge \K\d{4}' "$SHUTDOWN_CHECK_SCRIPT" 2>/dev/null | sort -u)

	if [[ -z "$thresholds" ]]; then
		echo "21 22"
		return
	fi

	local mon_wed_minutes thu_sun_minutes
	mon_wed_minutes=$(echo "$thresholds" | head -1) # 1260 (smaller = earlier = Mon-Wed)
	thu_sun_minutes=$(echo "$thresholds" | tail -1) # 1320 (larger = later = Thu-Sun)

	# Convert minutes to hours
	local mon_wed_hour=$((mon_wed_minutes / 60))
	local thu_sun_hour=$((thu_sun_minutes / 60))

	echo "$mon_wed_hour $thu_sun_hour"
}

# Get current time info
current_hour=$(date +%H)
current_minute=$(date +%M)
current_time_minutes=$((10#$current_hour * 60 + 10#$current_minute))
day_of_week=$(date +%u) # 1=Monday, 7=Sunday

# Get shutdown hours dynamically
read -r mon_wed_hour thu_sun_hour <<<"$(get_shutdown_hours)"

# Determine shutdown hour based on day of week
if [[ $day_of_week -ge 1 ]] && [[ $day_of_week -le 3 ]]; then
	# Monday-Wednesday
	shutdown_hour=$mon_wed_hour
else
	# Thursday-Sunday
	shutdown_hour=$thu_sun_hour
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

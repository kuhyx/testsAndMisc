#!/bin/bash

# CPU Temperature
cpu_temp=$(sensors | awk '/^Tctl:/ {print $2}' | tr -d '+°C')
if [ -z "$cpu_temp" ]; then
    cpu_temp=$(sensors | awk '/^Package id 0:/ {print $4}' | tr -d '+°C')
fi
if [ -z "$cpu_temp" ]; then
    cpu_temp=$(sensors | awk '/^Core 0:/ {print $3}' | tr -d '+°C')
fi
if [ -z "$cpu_temp" ]; then
    cpu_temp="N/A"
fi

# CPU Load (1-minute average)
cpu_load=$(awk '{print $1}' /proc/loadavg)
if [ -z "$cpu_load" ]; then
    cpu_load="N/A"
fi

# Colors for CPU Load
cpu_color="#FFFFFF"  # Default color
if [[ "$cpu_load" != "N/A" ]]; then
    # Add logic to change color based on load
    :
fi

echo -e "<span color=\"$cpu_color\">  CPU: ${cpu_temp}°C, Load: ${cpu_load}</span>"
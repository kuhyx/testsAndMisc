#!/bin/bash

# CPU Temperature
cpu_temp=$(sensors | awk '/^Tctl:/ {print $2}' | tr -d '+°C')
if [ -z "$cpu_temp" ]; then
    cpu_temp=$(sensors | awk '/^Package id 0:/ {print $3}' | tr -d '+°C')
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

cpu_metrics=$(echo "CPU Temp: $cpu_temp°C, CPU Load: $cpu_load, Color: $cpu_color")
cpu_temp=$(echo "$cpu_metrics" | awk -F', ' '{print $1}' | awk -F': ' '{print $2}')
cpu_load=$(echo "$cpu_metrics" | awk -F', ' '{print $2}' | awk -F': ' '{print $2}')
cpu_color=$(echo "$cpu_metrics" | awk -F', ' '{print $3}' | awk -F': ' '{print $2}')
echo -e "<span color=\"$cpu_color\">  CPU: ${cpu_temp}, Load: ${cpu_load}</span>"
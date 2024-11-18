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

# Colors for CPU Load and Temperature
cpu_color="#FFFFFF"  # Default color

# Change color based on CPU load
if [[ "$cpu_load" != "N/A" ]]; then
    cpu_load_float=$(echo "$cpu_load" | awk '{print ($1 + 0)}')
    if (( $(echo "$cpu_load_float < 1.0" | bc -l) )); then
        cpu_color="#50FA7B"  # Green for low load
    elif (( $(echo "$cpu_load_float < 2.0" | bc -l) )); then
        cpu_color="#F1FA8C"  # Yellow for medium load
    else
        cpu_color="#FF5555"  # Red for high load
    fi
fi

# Change color based on CPU temperature
if [[ "$cpu_temp" != "N/A" ]]; then
    cpu_temp_float=$(echo "$cpu_temp" | awk '{print ($1 + 0)}')
    if (( $(echo "$cpu_temp_float < 65.0" | bc -l) )); then
        cpu_color="#50FA7B"  # Green for low temperature
    elif (( $(echo "$cpu_temp_float < 85.0" | bc -l) )); then
        cpu_color="#F1FA8C"  # Yellow for medium temperature
    else
        cpu_color="#FF5555"  # Red for high temperature
    fi
fi

echo -e "<span color=\"$cpu_color\">    ${cpu_temp}°C, ${cpu_load}</span>"
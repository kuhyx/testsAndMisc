#!/bin/bash

# CPU Temperature
cpu_temp=$(sensors | awk '/^Tctl:/ {print $2}' | tr -d '+°C')
if [ -z "$cpu_temp" ]; then
    cpu_temp="N/A"
fi

# CPU Load (1-minute average)
cpu_load=$(awk '{print $1}' /proc/loadavg)
if [ -z "$cpu_load" ]; then
    cpu_load="N/A"
fi

# GPU Temperature
gpu_temp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null)
if [ -z "$gpu_temp" ]; then
    gpu_temp="N/A"
fi

# GPU Load
gpu_load=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null)
if [ -z "$gpu_load" ]; then
    gpu_load="N/A"
fi

# Colors for CPU Load
cpu_color="#FFFFFF"  # Default color
if [[ "$cpu_load" != "N/A" ]]; then
    if (( $(echo "$cpu_load < 1.0" | bc -l) )); then
        cpu_color="#50FA7B"  # Green
    elif (( $(echo "$cpu_load < 2.0" | bc -l) )); then
        cpu_color="#F1FA8C"  # Yellow
    else
        cpu_color="#FF5555"  # Red
    fi
fi

# Colors for GPU Load
gpu_color="#FFFFFF"  # Default color
if [[ "$gpu_load" != "N/A" ]]; then
    if (( $(echo "$gpu_load < 50.0" | bc -l) )); then
        gpu_color="#50FA7B"  # Green
    elif (( $(echo "$gpu_load < 75.0" | bc -l) )); then
        gpu_color="#F1FA8C"  # Yellow
    else
        gpu_color="#FF5555"  # Red
    fi
fi

# Output
echo -e "<span color=\"$cpu_color\">  CPU: ${cpu_temp}°C, Load: ${cpu_load}</span> | <span color=\"$gpu_color\">  GPU: ${gpu_temp}°C, Load: ${gpu_load}%</span>"
echo
echo "#FFFFFF"  # Default color for fallback (ignored if markup is enabled)


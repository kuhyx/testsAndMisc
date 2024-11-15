#!/bin/bash

# CPU Metrics
cpu_metrics=$(bash /home/kuchy/i3-configuration/i3blocks/cpu_monitor.sh)
cpu_temp=$(echo "$cpu_metrics" | awk -F', ' '{print $1}' | awk -F': ' '{print $2}')
cpu_load=$(echo "$cpu_metrics" | awk -F', ' '{print $2}' | awk -F': ' '{print $2}')
cpu_color=$(echo "$cpu_metrics" | awk -F', ' '{print $3}' | awk -F': ' '{print $2}')

# GPU Metrics
gpu_metrics=$(bash /home/kuchy/i3-configuration/i3blocks/gpu_monitor.sh)
gpu_temp=$(echo "$gpu_metrics" | awk -F', ' '{print $1}' | awk -F': ' '{print $2}')
gpu_load=$(echo "$gpu_metrics" | awk -F', ' '{print $2}' | awk -F': ' '{print $2}')

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
echo -e "<span color=\"$cpu_color\">  CPU: ${cpu_temp}, Load: ${cpu_load}</span> | <span color=\"$gpu_color\">  GPU: ${gpu_temp}, Load: ${gpu_load}</span>"
echo
echo "#FFFFFF"  # Default color for fallback (ignored if markup is enabled)


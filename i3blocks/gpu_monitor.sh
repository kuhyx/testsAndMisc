#!/bin/bash

# Function to get NVIDIA GPU metrics
get_nvidia_metrics() {
    gpu_temp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null)
    if [ -z "$gpu_temp" ]; then
        gpu_temp="N/A"
    fi

    gpu_load=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null)
    if [ -z "$gpu_load" ]; then
        gpu_load="N/A"
    fi

    echo "GPU Temp: $gpu_temp°C, GPU Load: $gpu_load"
}

# Function to get Intel GPU metrics
get_intel_metrics() {
    gpu_load=$(cat /sys/class/drm/card0/device/gpu_busy_percent 2>/dev/null)
    if [ -z "$gpu_load" ]; then
        gpu_load="N/A"
    fi

    gpu_temp=$(sensors | awk '/^temp1:/ {print $2; exit}' | tr -d '+°C')
    if [ -z "$gpu_temp" ]; then
        gpu_temp="N/A"
    fi

    echo "GPU Temp: $gpu_temp°C, GPU Load: $gpu_load"
}

# Detect GPU type and get metrics
if lspci | grep -i nvidia > /dev/null; then
    gpu_metrics=$(get_nvidia_metrics)
elif lspci | grep -i vga | grep -i intel > /dev/null; then
    gpu_metrics=$(get_intel_metrics)
else
    echo "No supported GPU found."
fi

#!/bin/bash
# GPU Metrics
gpu_temp=$(echo "$gpu_metrics" | awk -F', ' '{print $1}' | awk -F': ' '{print $2}')
gpu_load=$(echo "$gpu_metrics" | awk -F', ' '{print $2}' | awk -F': ' '{print $2}')

gpu_color="#FFFFFF"  
# Colors for GPU Load
if [[ "$gpu_load" != "N/A" ]]; then
    if (( $(echo "$gpu_load < 50.0" | bc -l) )); then
        gpu_color="#50FA7B"  # Green
    elif (( $(echo "$gpu_load < 75.0" | bc -l) )); then
        gpu_color="#F1FA8C"  # Yellow
    else
        gpu_color="#FF5555"  # Red
    fi
else 
    gpu_color="#FFFFFF"  # Default color
fi

# Output<
echo -e "<span color=\"$gpu_color\"> ${gpu_temp}, ${gpu_load}%</span>"
echo
echo "#FFFFFF"  # Default color for fallback (ignored if markup is enabled)


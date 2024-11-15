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

    echo "GPU Temp: $gpu_temp°C, GPU Load: $gpu_load%"
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

    echo "GPU Temp: $gpu_temp°C, GPU Load: $gpu_load%"
}

# Detect GPU type and get metrics
if lspci | grep -i nvidia > /dev/null; then
    get_nvidia_metrics
elif lspci | grep -i vga | grep -i intel > /dev/null; then
    get_intel_metrics
else
    echo "No supported GPU found."
fi
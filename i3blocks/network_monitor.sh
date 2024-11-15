#!/bin/bash

# Function to detect the active network interface
detect_interface() {
    for interface in /sys/class/net/*; do
        interface=$(basename "$interface")
        if [[ "$interface" != "lo" && -d "/sys/class/net/$interface" && "$(cat /sys/class/net/$interface/operstate)" == "up" ]]; then
            echo "$interface"
            return
        fi
    done
}

# Detect the active network interface
interface=$(detect_interface)

# If no active interface is found, exit
if [ -z "$interface" ]; then
    echo "No active network interface found"
    exit 1
fi

# Paths to RX (received) and TX (transmitted) bytes
rx_path="/sys/class/net/$interface/statistics/rx_bytes"
tx_path="/sys/class/net/$interface/statistics/tx_bytes"

# Read the current RX and TX bytes
rx_now=$(cat $rx_path 2>/dev/null)
tx_now=$(cat $tx_path 2>/dev/null)

# Read the last recorded RX and TX bytes from a temp file
state_file="/tmp/network_monitor_$interface"
if [ -f "$state_file" ]; then
    read last_rx last_tx last_time < "$state_file"
else
    last_rx=$rx_now
    last_tx=$tx_now
    last_time=$(date +%s)
fi

# Save current RX and TX bytes for the next check
current_time=$(date +%s)
echo "$rx_now $tx_now $current_time" > "$state_file"

# Calculate time difference
time_diff=$((current_time - last_time))

# Calculate download and upload speeds in bytes per second
if (( time_diff > 0 )); then
    rx_rate=$(( (rx_now - last_rx) / time_diff ))
    tx_rate=$(( (tx_now - last_tx) / time_diff ))
else
    rx_rate=0
    tx_rate=0
fi

# Convert speeds to human-readable format
rx_rate_human=$(numfmt --to=iec --suffix=B/s $rx_rate)
tx_rate_human=$(numfmt --to=iec --suffix=B/s $tx_rate)

# Output the result with fixed width
printf "  DL: %-8s      UL: %-8s\n" "$rx_rate_human" "$tx_rate_human"
echo "#50FA7B"
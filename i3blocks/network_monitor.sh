#!/bin/bash

# Ethernet interface (replace with your interface name, e.g., enp6s0)
interface="enp6s0"

# Paths to RX (received) and TX (transmitted) bytes
rx_path="/sys/class/net/$interface/statistics/rx_bytes"
tx_path="/sys/class/net/$interface/statistics/tx_bytes"

# Read the current RX and TX bytes
rx_now=$(cat $rx_path)
tx_now=$(cat $tx_path)

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

# Convert to human-readable format (KB/s or MB/s) with consistent width
rx_human=$(numfmt --to=iec --suffix=B/s --format="%7.1f" $rx_rate)
tx_human=$(numfmt --to=iec --suffix=B/s --format="%7.1f" $tx_rate)

# Output the data with consistent padding
printf "  DL: %-10s   UL: %-10s\n" "$rx_human" "$tx_human"
echo
echo "#50FA7B"


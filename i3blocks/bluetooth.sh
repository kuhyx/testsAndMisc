#!/bin/bash

# Get Bluetooth device info
bluetooth_info=$(bluetoothctl info)

# Check if Bluetooth is connected
if echo "$bluetooth_info" | grep -q "Connected: yes"; then
    device=$(echo "$bluetooth_info" | grep "Alias" | cut -d ' ' -f2-)
    echo " $device"  #  is the Bluetooth icon
    echo
    echo "#50FA7B"  # Green for connected
else
    echo " Disconnected"
    echo
    echo "#FF5555"  # Red for disconnected
fi


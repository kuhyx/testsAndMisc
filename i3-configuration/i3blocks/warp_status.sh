#!/bin/bash

# Check if warp-cli is installed
if ! command -v warp-cli &> /dev/null; then
    echo "  N/A"
    exit 0
fi

# Get the status from warp-cli
status=$(warp-cli status 2>/dev/null | grep "Status update:" | awk '{print $3}')

# Display the status with an icon
if [ "$status" = "Connected" ]; then
    echo "!!!  WARP CONNECTED !!!"
    echo
    echo "#FFFF00"  # Yellow
elif [ "$status" = "Disconnected" ]; then
    echo "warp disconnected"
else
    echo "!  WARP unknown !"
    echo
    echo "#FF0000"  # Yellow
    exit 0
fi

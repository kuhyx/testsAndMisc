#!/bin/bash

# Get the first temp1 value from sensors
temp=$(sensors | awk '/^temp1:/ {print $2; exit}' | tr -d '+°C')

# Ensure the temperature is a valid number
if [[ ! "$temp" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "  MB: N/A"
    echo
    echo "#FF5555"  # Red color for error
    exit 1
fi

# Define temperature thresholds
if (( $(echo "$temp < 50.0" | bc -l) )); then
    color="#50FA7B"  # Green for OK temperature
elif (( $(echo "$temp < 70.0" | bc -l) )); then
    color="#F1FA8C"  # Yellow for warning temperature
else
    color="#FF5555"  # Red for high temperature
fi

# Output the temperature with the color
echo "  ${temp}°C"  #  is a thermometer icon
echo
echo $color


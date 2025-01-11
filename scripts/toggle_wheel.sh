#!/bin/bash

# Replace these with your device's vendor and product IDs
VENDOR_ID="c24f"
PRODUCT_ID="046d"

ACTION=$1

# Check if script is run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root. Please run with sudo."
   exit 1
fi

# Check if action parameter is provided
if [[ "$ACTION" != "on" && "$ACTION" != "off" ]]; then
    echo "Usage: $0 [on|off]"
    exit 1
fi

DEVICE_PATH=""

# Find the device path in sysfs
for sysdevpath in $(find /sys/bus/usb/devices/ -name idVendor); do
    if [[ $(cat "$sysdevpath") == "$VENDOR_ID" ]]; then
        parentdir="$(dirname "$sysdevpath")"
        if [[ $(cat "$parentdir/idProduct") == "$PRODUCT_ID" ]]; then
            DEVICE_PATH="$parentdir"
            break
        fi
    fi
done

# Check if device was found
if [ -z "$DEVICE_PATH" ]; then
    echo "Device with Vendor ID $VENDOR_ID and Product ID $PRODUCT_ID not found."
    exit 1
fi

# Enable or disable the device
if [ "$ACTION" == "off" ]; then
    echo '0' > "$DEVICE_PATH/authorized"
    echo "Device turned off."
elif [ "$ACTION" == "on" ]; then
    echo '1' > "$DEVICE_PATH/authorized"
    echo "Device turned on."
fi
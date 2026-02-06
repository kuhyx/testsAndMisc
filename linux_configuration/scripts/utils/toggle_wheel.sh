#!/bin/bash

# Replace these with your device's vendor and product IDs
# Note: lsusb prints as VENDOR:PRODUCT (e.g., 046d:c24f for Logitech G29)
#       sysfs expects idVendor=046d and idProduct=c24f
VENDOR_ID="046d"
PRODUCT_ID="c24f"

ACTION=$1

# Check if script is run as root
if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root. Please run with sudo."
  exit 1
fi

# Check if action parameter is provided
if [[ $ACTION != "on" && $ACTION != "off" ]]; then
  echo "Usage: $0 [on|off]"
  exit 1
fi

DEVICE_PATH=""

# Find the device path in sysfs (robust scan)
for d in /sys/bus/usb/devices/*; do
  if [[ -f "$d/idVendor" && -f "$d/idProduct" ]]; then
    v=$(cat "$d/idVendor")
    p=$(cat "$d/idProduct")
    if [[ $v == "$VENDOR_ID" && $p == "$PRODUCT_ID" ]]; then
      DEVICE_PATH="$d"
      break
    fi
  fi
done

# Check if device was found
if [ -z "$DEVICE_PATH" ]; then
  echo "Device with Vendor ID $VENDOR_ID and Product ID $PRODUCT_ID not found in /sys/bus/usb/devices."
  echo "Tip: Run 'lsusb | grep ${VENDOR_ID}:${PRODUCT_ID}' to verify it's connected."
  exit 1
fi

# Enable or disable the device
if [ ! -e "$DEVICE_PATH/authorized" ]; then
  echo "The 'authorized' attribute is not present at $DEVICE_PATH."
  echo "This device may not support toggling via 'authorized'."
  exit 1
fi

if [ "$ACTION" == "off" ]; then
  echo '0' > "$DEVICE_PATH/authorized"
  echo "Device at $(basename "$DEVICE_PATH") turned off."
elif [ "$ACTION" == "on" ]; then
  echo '1' > "$DEVICE_PATH/authorized"
  echo "Device at $(basename "$DEVICE_PATH") turned on."
fi

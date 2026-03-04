#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# No pip dependencies — script only uses stdlib (+pyusb for fallback info)
# Requires root for USB access (PJL via usblp or port status via pyusb)
# Usage: ./run.sh              # auto-detect
#        ./run.sh <printer_ip> # network/SNMP mode

# Use sudo when a Brother printer is on USB (for /dev/usb/lp* or pyusb hw query)
if ls /dev/usb/lp* &>/dev/null || lsusb 2>/dev/null | grep -qi "04f9.*brother"; then
    echo "Note: sudo may prompt for your password (required for USB printer access)."
    sudo python3 "$SCRIPT_DIR/check_brother_printer.py" "$@"
else
    python3 "$SCRIPT_DIR/check_brother_printer.py" "$@"
fi

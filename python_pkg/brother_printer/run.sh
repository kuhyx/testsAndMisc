#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# No pip dependencies — script only uses stdlib (+pyusb for fallback info)
# Requires root for USB hardware queries and CUPS management
# Usage: ./run.sh              # auto-detect
#        ./run.sh <printer_ip> # network/SNMP mode

if [[ $EUID -ne 0 ]]; then
    exec sudo python3 "$SCRIPT_DIR/check_brother_printer.py" "$@"
fi
exec python3 "$SCRIPT_DIR/check_brother_printer.py" "$@"

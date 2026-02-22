#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# No pip dependencies — script only uses stdlib
# Requires root for USB mode; pass printer IP as argument for network/SNMP mode
# Usage: ./run.sh              # auto-detect
#        ./run.sh <printer_ip> # network/SNMP mode
echo "Note: sudo may prompt for your password (required for USB printer access)."
sudo python3 "$SCRIPT_DIR/check_brother_printer.py" "$@"

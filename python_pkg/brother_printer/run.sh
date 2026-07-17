#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# No pip dependencies — script only uses stdlib (+pyusb for fallback info)
# Requires root for USB hardware queries and CUPS management
#
# Imports are absolute (python_pkg.brother_printer.*), so the monorepo root must
# be importable. sudo's env_reset drops an exported PYTHONPATH, hence passing it
# as a sudo VAR=value argument instead.
#
# Usage: ./run.sh              # auto-detect
#        ./run.sh <printer_ip> # network/SNMP mode

if [[ $EUID -ne 0 ]]; then
    exec sudo PYTHONPATH="$REPO_ROOT" python3 -m python_pkg.brother_printer "$@"
fi
exec env PYTHONPATH="$REPO_ROOT" python3 -m python_pkg.brother_printer "$@"

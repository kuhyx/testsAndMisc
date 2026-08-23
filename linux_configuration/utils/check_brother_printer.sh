#!/usr/bin/env bash
# Check Brother laser printer consumable/maintenance status.
# Thin wrapper that ensures dependencies are present, then runs the
# Python implementation in ~/testsAndMisc/python_pkg/brother_printer.
#
# Usage:
#   ./check_brother_printer.sh              # auto-detect USB or network
#   ./check_brother_printer.sh <printer_ip> # force network/SNMP mode

set -euo pipefail

PYTHON_PKG_DIR="${HOME}/testsAndMisc/python_pkg"
BROTHER_MODULE="brother_printer"

# ── Ensure dependencies ─────────────────────────────────────────────

check_dependency() {
	local cmd="$1" pkg="$2"
	if ! command -v "$cmd" &>/dev/null; then
		echo "Installing $pkg..."
		sudo pacman -S --noconfirm --needed "$pkg"
	fi
}

check_dependency python3 python
check_dependency lsusb usbutils

# net-snmp is optional (only needed for network mode)
if [[ -n "${1:-}" ]] && ! command -v snmpwalk &>/dev/null; then
	echo "Installing net-snmp (needed for network mode)..."
	sudo pacman -S --noconfirm --needed net-snmp
fi

# ── Verify the Python module exists ──────────────────────────────────

if [[ ! -f "${PYTHON_PKG_DIR}/${BROTHER_MODULE}/check_brother_printer.py" ]]; then
	echo "Error: Python module not found at ${PYTHON_PKG_DIR}/${BROTHER_MODULE}/" >&2
	exit 1
fi

# ── Run (with sudo for USB access) ──────────────────────────────────

if [[ $EUID -ne 0 ]]; then
	exec sudo bash -c "cd '$PYTHON_PKG_DIR' && python3 -m '$BROTHER_MODULE' $*"
fi

cd "$PYTHON_PKG_DIR"
exec python3 -m "$BROTHER_MODULE" "$@"

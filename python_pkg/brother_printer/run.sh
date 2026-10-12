#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Depends on pyusb (USB port-status probe when CUPS owns the printer) and runs
# as root for USB hardware queries and CUPS management.
#
# Imports are absolute (python_pkg.brother_printer.*), so the monorepo root must
# be importable. sudo's env_reset drops an exported PYTHONPATH, hence passing it
# as a sudo VAR=value argument instead.
#
# Usage: ./run.sh              # auto-detect
#        ./run.sh <printer_ip> # network/SNMP mode

# The tool runs under the system python3 (sudo secure_path), so pyusb must come
# from the distro package, not a venv.
ensure_pyusb() {
	/usr/bin/python3 -c 'import usb.core' 2>/dev/null && return 0
	if ! command -v pacman >/dev/null; then
		echo "pyusb missing and pacman not found; install python-pyusb for system python3." >&2
		exit 1
	fi
	echo "Installing python-pyusb..."
	sudo pacman -S --needed --noconfirm python-pyusb
}

ensure_pyusb

if [[ $EUID -ne 0 ]]; then
	exec sudo PYTHONPATH="$REPO_ROOT" python3 -m python_pkg.brother_printer "$@"
fi
exec env PYTHONPATH="$REPO_ROOT" python3 -m python_pkg.brother_printer "$@"

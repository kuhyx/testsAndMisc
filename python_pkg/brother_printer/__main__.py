"""Brother laser printer status checker.

Usage:
    sudo python3 -m python_pkg.brother_printer              # auto-detect
    sudo python3 -m python_pkg.brother_printer <printer_ip> # network/SNMP mode
"""

from __future__ import annotations

from python_pkg.brother_printer.check_brother_printer import main

if __name__ == "__main__":
    main()

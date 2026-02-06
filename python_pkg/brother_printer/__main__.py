"""Brother laser printer status checker.

Usage:
    sudo python3 -m brother_printer              # auto-detect
    sudo python3 -m brother_printer <printer_ip>  # network/SNMP mode
"""

from brother_printer.check_brother_printer import main

main()

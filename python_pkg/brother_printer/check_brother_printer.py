"""Check Brother laser printer consumable/maintenance status.

Supports both USB-connected and network printers on Arch Linux.
Requires root (sudo) for USB hardware queries and CUPS management.

USB:     Queries via PJL over /dev/usb/lp* (requires usblp module).
         Falls back to USB port status query + CUPS IPP when usblp is unavailable.
Network: Queries via SNMP (requires net-snmp).

Usage:
    sudo python3 -m brother_printer              # auto-detect USB or network
    sudo python3 -m brother_printer <printer_ip>  # force network/SNMP mode
    sudo python3 -m brother_printer --reset-toner # after replacing toner
    sudo python3 -m brother_printer --reset-drum  # after replacing drum

This module re-exports public symbols from sub-modules for backwards
compatibility.  The implementation lives in:

- constants.py      - colours, PJL status codes, lookup tables
- data_classes.py   - dataclasses (CUPSJob, USBResult, NetworkResult ...)
- usb_query.py      - USB discovery and PJL query
- cups_service.py   - CUPS service control, consumable state, USB fallback
- network_query.py  - SNMP network query
- cups_queue.py     - CUPS queue inspection and interactive fixes
- display.py        - formatted output for USB / network results
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys

from python_pkg.brother_printer.constants import CYAN, RED, RESET, _out
from python_pkg.brother_printer.cups_service import reset_consumable
from python_pkg.brother_printer.display import (
    display_network_results,
    display_usb_results,
)
from python_pkg.brother_printer.network_query import query_network_snmp
from python_pkg.brother_printer.usb_query import find_brother_usb, query_usb_pjl

logger = logging.getLogger(__name__)


# ── Main ─────────────────────────────────────────────────────────────


def _discover_network_printer() -> str:
    """Try to discover a network printer IP via CUPS."""
    lpstat_path = shutil.which("lpstat")
    if not lpstat_path:
        return ""
    try:
        r = subprocess.run(
            [lpstat_path, "-v"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        match = re.search(
            r"(?:ipp|socket|lpd|http)://" r"(\d+\.\d+\.\d+\.\d+)",
            r.stdout,
        )
        if match:
            return match.group(1)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        logger.debug("Failed to discover printer via CUPS", exc_info=True)
    return ""


def _run_network_mode(printer_ip: str) -> None:
    """Handle explicit network/SNMP mode."""
    if not shutil.which("snmpwalk"):
        _out(f"{RED}snmpwalk not found. Install: sudo pacman -S net-snmp{RESET}")
        sys.exit(1)
    _out(f"{CYAN}Querying printer at {printer_ip} via SNMP...{RESET}")
    display_network_results(query_network_snmp(printer_ip))


def _run_usb_mode(usb_line: str) -> None:
    """Handle USB printer mode."""
    _out(f"{CYAN}Found Brother printer on USB: {usb_line}{RESET}")
    display_usb_results(query_usb_pjl())


def _no_printer_found() -> None:
    """Print error message when no printer is detected."""
    _out(f"{RED}No Brother printer found.{RESET}")
    _out()
    _out("Ensure the printer is:")
    _out("  \u2022 Powered on")
    _out("  \u2022 Connected via USB or on the same network")
    _out()
    _out("Usage: python3 -m brother_printer [printer_ip]")
    sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    """Entry point: auto-detect USB or network Brother printer."""
    args = argv if argv is not None else sys.argv[1:]

    if args and args[0] == "--reset-toner":
        reset_consumable("toner")
        return
    if args and args[0] == "--reset-drum":
        reset_consumable("drum")
        return

    if os.geteuid() != 0:
        _out(
            f"{RED}Root access required. Re-run with sudo:{RESET}\n"
            f"  sudo python3 -m brother_printer {' '.join(args)}".rstrip(),
        )
        sys.exit(1)

    printer_ip = args[0] if args else ""

    if printer_ip:
        _run_network_mode(printer_ip)
        return

    usb_line = find_brother_usb()
    if usb_line:
        _run_usb_mode(usb_line)
        return

    network_ip = _discover_network_printer()
    if network_ip and shutil.which("snmpwalk"):
        _out(f"{CYAN}Found network printer at {network_ip}{RESET}")
        display_network_results(query_network_snmp(network_ip))
        return

    _no_printer_found()


if __name__ == "__main__":
    main()

"""Check Brother laser printer consumable/maintenance status.

Supports both USB-connected and network printers on Arch Linux.

USB:     Queries via PJL over /dev/usb/lp* (requires root).
Network: Queries via SNMP (requires net-snmp).

Usage:
    sudo python3 -m brother_printer              # auto-detect USB or network
    sudo python3 -m brother_printer <printer_ip>  # force network/SNMP mode
    sudo python3 brother_printer.py               # run directly
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import fcntl
import logging
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING
import urllib.parse

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# ── Colors ───────────────────────────────────────────────────────────

RED = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── SNMP supply level sentinel values ────────────────────────────────────────

SNMP_LEVEL_OK = -3
SNMP_LEVEL_LOW = -2
SUPPLY_LOW_PCT = 10
SUPPLY_WARN_PCT = 25
PROGRESS_BAR_WIDTH = 25


def _out(text: str = "") -> None:
    """Write a line to stdout."""
    sys.stdout.write(text + "\n")


# ── Brother PJL status codes ────────────────────────────────────────
# Documented in Brother PJL Technical Reference.
# Format: code -> (severity, short_text, action)
# Severities: ok, info, warn, critical

BROTHER_STATUS_CODES: dict[int, tuple[str, str, str]] = {
    10001: ("ok", "Ready", ""),
    10002: ("ok", "Sleep", ""),
    10003: ("info", "Self-test / Calibrating", ""),
    10004: ("ok", "Warming up", ""),
    10005: ("ok", "Cooling down", ""),
    10006: ("info", "Processing", ""),
    10007: ("info", "Printing", ""),
    10014: ("ok", "Cancelling", ""),
    10023: ("info", "Waiting", ""),
    # Toner
    30010: (
        "warn",
        "Toner Low",
        "Order replacement toner cartridge (TN-1050/TN-1030 compatible).",
    ),
    30038: (
        "warn",
        "Toner Low",
        "Order replacement toner cartridge (TN-1050/TN-1030 compatible).",
    ),
    40038: (
        "warn",
        "Toner Low",
        "Order replacement toner cartridge (TN-1050/TN-1030 compatible).",
    ),
    40309: (
        "critical",
        "Replace Toner",
        "The toner cartridge needs immediate replacement"
        " (TN-1050/TN-1030 compatible).",
    ),
    40310: (
        "critical",
        "Toner End",
        "The toner cartridge is empty. Replace now" " (TN-1050/TN-1030 compatible).",
    ),
    # Drum
    30201: (
        "warn",
        "Drum End Soon",
        "The drum unit is nearing end of life."
        " Order replacement (DR-1050 compatible).",
    ),
    40201: (
        "warn",
        "Drum End Soon",
        "The drum unit is nearing end of life."
        " Order replacement (DR-1050 compatible).",
    ),
    40019: (
        "critical",
        "Replace Drum",
        "The drum unit must be replaced (DR-1050 compatible).",
    ),
    40020: (
        "critical",
        "Drum Stop",
        "The drum unit must be replaced immediately (DR-1050 compatible).",
    ),
    # Paper / feed
    40000: ("critical", "Paper Jam", "Clear the paper jam and close all covers."),
    40300: (
        "critical",
        "No Paper / Tray Open",
        "Load paper or close the paper tray.",
    ),
    40302: ("critical", "No Paper", "Load paper into the paper tray."),
    40016: ("warn", "Paper Feed Error", "Check paper tray and re-seat paper."),
    # Cover
    41000: ("critical", "Cover Open", "Close the top cover of the printer."),
    41001: ("critical", "Cover Open", "Close the front cover of the printer."),
    # Others
    35078: ("info", "Manual Feed", "Load paper in the manual feed slot."),
    42000: (
        "critical",
        "Machine Error",
        "Power-cycle the printer. If error persists, contact service.",
    ),
}


# ── Data classes ─────────────────────────────────────────────────────


@dataclass
class USBResult:
    """Result from a USB PJL query."""

    connection: str = "usb"
    device: str = ""
    product: str = "Brother Laser Printer"
    serial: str = ""
    status_code: str = ""
    display: str = ""
    online: str = ""
    economode: str = ""
    error: str = ""


@dataclass
class NetworkResult:
    """Result from an SNMP network query."""

    connection: str = "network"
    ip: str = ""
    product: str = "Unknown"
    serial: str = ""
    printer_status: str = ""
    device_status: str = ""
    display: str = ""
    page_count: str = ""
    supply_descriptions: list[str] = field(default_factory=list)
    supply_max: list[str] = field(default_factory=list)
    supply_levels: list[str] = field(default_factory=list)
    error: str = ""


# ── USB printer discovery ────────────────────────────────────────────


def find_brother_usb() -> str:
    """Look for any Brother printer on USB via lsusb. Returns the info line."""
    if not shutil.which("lsusb"):
        return ""
    try:
        r = subprocess.run(
            ["lsusb"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if "04f9:" in line.lower():
                # Return the part after "ID ..."
                return line.split(": ", 1)[1] if ": " in line else line
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def find_usb_printer_dev() -> str | None:
    """Find /dev/usb/lp* device for the Brother printer."""
    devices = sorted(Path("/dev/usb").glob("lp*"))
    return str(devices[0]) if devices else None


def get_printer_info_from_cups() -> dict[str, str]:
    """Get printer model/serial from lpstat."""
    info: dict[str, str] = {"product": "", "serial": ""}
    try:
        r = subprocess.run(
            ["lpstat", "-v"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if "Brother" not in line:
                continue
            for part in line.split():
                if part.startswith("usb://"):
                    parsed = urllib.parse.urlparse(part)
                    info["product"] = urllib.parse.unquote(parsed.path.lstrip("/"))
                    qs = urllib.parse.parse_qs(parsed.query)
                    if "serial" in qs:
                        info["serial"] = qs["serial"][0]
                    break
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        logger.debug("Failed to query CUPS for printer info", exc_info=True)
    return info


# ── PJL over USB ─────────────────────────────────────────────────────


def _drain_buffer(fd: int) -> None:
    """Read and discard any stale data from the USB buffer."""
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    with contextlib.suppress(OSError):
        while os.read(fd, 4096):
            pass
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)


def pjl_query(fd: int, cmd: str, timeout_sec: float = 5.0) -> str:
    """Send a PJL command via raw fd and read the response.

    Uses select() to wait for data availability instead of polling.
    """
    # Ensure blocking mode for write
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)

    pjl_cmd = f"\x1b%-12345X@PJL\r\n{cmd}\r\n\x1b%-12345X"
    os.write(fd, pjl_cmd.encode())

    # Wait for data to become available using select()
    response = b""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        readable, _, _ = select.select([fd], [], [], min(remaining, 1.0))
        if readable:
            # Switch to non-blocking to read all available data
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            with contextlib.suppress(OSError):
                while True:
                    chunk = os.read(fd, 4096)
                    if chunk:
                        response += chunk
                    else:
                        break
            fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
            # If we got meaningful PJL data, stop waiting
            if response and (b"=" in response or b"@PJL" in response):
                break

    # Restore blocking mode
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
    return response.decode("ascii", errors="replace")


def _parse_status(resp: str, result: USBResult) -> bool:
    """Parse STATUS response into result. Returns True if code was found."""
    found = False
    for raw_line in resp.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("CODE="):
            result.status_code = stripped.split("=", 1)[1]
            found = True
        elif stripped.startswith("DISPLAY="):
            result.display = stripped.split("=", 1)[1].strip().strip('"').strip()
        elif stripped.startswith("ONLINE="):
            result.online = stripped.split("=", 1)[1]
    return found


def _parse_variables(resp: str, result: USBResult) -> bool:
    """Parse VARIABLES response into result. Returns True if data found."""
    found = False
    for raw_line in resp.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("ECONOMODE="):
            result.economode = stripped.split("=", 1)[1].split()[0]
            found = True
    return found


def _retry_pjl_query(
    fd: int,
    cmd: str,
    parser: Callable[[str, USBResult], bool],
    result: USBResult,
    max_retries: int,
) -> None:
    """Send a PJL query with retries, draining between attempts."""
    for attempt in range(max_retries + 1):
        resp = pjl_query(fd, cmd)
        if parser(resp, result):
            break
        if attempt < max_retries:
            _drain_buffer(fd)
            time.sleep(0.5)


def query_usb_pjl(max_retries: int = 2) -> USBResult:
    """Query a Brother printer via PJL over /dev/usb/lp*."""
    dev_path = find_usb_printer_dev()
    if not dev_path:
        return USBResult(error="No USB printer device found at /dev/usb/lp*")

    cups_info = get_printer_info_from_cups()
    result = USBResult(
        device=dev_path,
        product=cups_info.get("product") or "Brother Laser Printer",
        serial=cups_info.get("serial", ""),
    )

    if not os.access(dev_path, os.R_OK | os.W_OK):
        result.error = f"Permission denied: {dev_path}. Run with sudo."
        return result

    fd: int | None = None
    try:
        fd = os.open(dev_path, os.O_RDWR)
        fcntl.fcntl(fd, fcntl.F_GETFL)

        # Drain any stale data in the USB buffer
        _drain_buffer(fd)

        # Wake-up: send a bare UEL to get the printer's attention
        os.write(fd, b"\x1b%-12345X@PJL\r\n\x1b%-12345X")
        time.sleep(0.5)
        _drain_buffer(fd)

        _retry_pjl_query(fd, "@PJL INFO STATUS", _parse_status, result, max_retries)
        _drain_buffer(fd)
        time.sleep(0.5)
        _retry_pjl_query(
            fd, "@PJL INFO VARIABLES", _parse_variables, result, max_retries
        )

    except OSError as e:
        result.error = str(e)
    finally:
        if fd is not None:
            os.close(fd)

    return result


# ── SNMP network query ──────────────────────────────────────────────


def snmp_walk(ip: str, oid: str, community: str, timeout: int) -> list[str]:
    """Run snmpwalk and return cleaned values."""
    snmpwalk_path = shutil.which("snmpwalk")
    if not snmpwalk_path:
        return []
    try:
        r = subprocess.run(
            [
                snmpwalk_path,
                "-v",
                "2c",
                "-c",
                community,
                "-t",
                str(timeout),
                "-OQvs",
                ip,
                oid,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return [
            line.strip().strip('"')
            for line in r.stdout.strip().splitlines()
            if line.strip()
        ]
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return []


def query_network_snmp(ip: str) -> NetworkResult:
    """Query a Brother printer via SNMP over the network."""
    community = "public"
    timeout = 5

    # Quick connectivity check
    snmpget_path = shutil.which("snmpget")
    if not snmpget_path:
        return NetworkResult(
            ip=ip,
            error="snmpget not found. Install: sudo pacman -S net-snmp",
        )
    try:
        subprocess.run(
            [
                snmpget_path,
                "-v",
                "2c",
                "-c",
                community,
                "-t",
                str(timeout),
                ip,
                "1.3.6.1.2.1.43.11.1.1.6.1.1",
            ],
            capture_output=True,
            timeout=10,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return NetworkResult(ip=ip, error=f"Cannot reach printer at {ip} via SNMP.")

    def walk(oid: str) -> list[str]:
        return snmp_walk(ip, oid, community, timeout)

    return NetworkResult(
        ip=ip,
        product=" ".join(walk("1.3.6.1.2.1.25.3.2.1.3")[:1]) or "Unknown",
        serial=" ".join(walk("1.3.6.1.2.1.43.5.1.1.17")[:1]) or "",
        printer_status=" ".join(walk("1.3.6.1.2.1.25.3.5.1.1")[:1]) or "",
        device_status=" ".join(walk("1.3.6.1.2.1.25.3.2.1.5")[:1]) or "",
        display=" ".join(walk("1.3.6.1.2.1.43.16.5.1.2")[:3]) or "",
        page_count=" ".join(walk("1.3.6.1.2.1.43.10.2.1.4")[:1]) or "",
        supply_descriptions=walk("1.3.6.1.2.1.43.11.1.1.6"),
        supply_max=walk("1.3.6.1.2.1.43.11.1.1.8"),
        supply_levels=walk("1.3.6.1.2.1.43.11.1.1.9"),
    )


# ── Status code lookup ──────────────────────────────────────────────


def get_status_info(code: str) -> tuple[str, str, str]:
    """Look up a PJL status code. Returns (severity, text, action)."""
    try:
        return BROTHER_STATUS_CODES[int(code)]
    except (KeyError, ValueError):
        return (
            "info",
            f"Unknown status (code {code})",
            "Check printer display for details.",
        )


# ── Display: shared helpers ─────────────────────────────────────────


def _display_report_header() -> None:
    """Print the report banner box."""
    _out()
    _out(f"{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    _out(f"{BOLD}║      Brother Laser Printer Status Report         ║{RESET}")
    _out(f"{BOLD}╚══════════════════════════════════════════════════╝{RESET}")
    _out()


def _display_consumables_reference() -> None:
    """Print compatible consumables reference."""
    _out(f"{BOLD}── Compatible Consumables ──{RESET}")
    _out()
    _out(f"  {BOLD}Toner:{RESET} TN-1050 / TN-1030 (or compatible third-party)")
    _out(f"  {BOLD}Drum:{RESET}  DR-1050 / DR-1030 (or compatible third-party)")
    _out(f"  {DIM}  Toner rated ~1000 pages; Drum rated ~10000 pages.{RESET}")
    _out()


# ── Display: USB helpers ────────────────────────────────────────────


def _display_usb_device_info(result: USBResult) -> None:
    """Print device info block for USB results."""
    _out(f"{BOLD}Printer:{RESET}    {result.product or 'Unknown'}")
    _out(f"{BOLD}Connection:{RESET} USB")
    if result.serial:
        _out(f"{BOLD}Serial:{RESET}     {result.serial}")

    if result.online == "TRUE":
        _out(f"{BOLD}Online:{RESET}     {GREEN}Yes{RESET}")
    elif result.online == "FALSE":
        _out(f"{BOLD}Online:{RESET}     {YELLOW}No (needs attention){RESET}")

    _out()

    if result.economode:
        if result.economode == "ON":
            _out(
                f"{BOLD}Toner Save:{RESET} {GREEN}ON{RESET}"
                " (extends toner life, lighter prints)"
            )
        else:
            _out(f"{BOLD}Toner Save:{RESET} OFF")


def _display_pjl_status(result: USBResult) -> None:
    """Display PJL status code interpretation."""
    _out()
    _out(f"{BOLD}── Printer Status ──{RESET}")
    _out()

    if not result.status_code:
        _out(f"  {YELLOW}Could not read status from printer.{RESET}")
        if result.display:
            _out(f"  Display message: {BOLD}{result.display}{RESET}")
        return

    severity, short_text, action = get_status_info(result.status_code)

    icons = {"ok": "✓", "info": "i", "warn": "⚡", "critical": "⚠"}
    colors = {"ok": GREEN, "info": CYAN, "warn": YELLOW, "critical": RED}
    color = colors.get(severity, GREEN)
    icon = icons.get(severity, "✓")

    _out(f"  {color}{BOLD}{icon}  {short_text}{RESET}")
    if result.display and result.display != short_text:
        _out(f"  {DIM}Display: {result.display}{RESET}")
    _out(f"  {DIM}Status code: {result.status_code}{RESET}")

    if action:
        _out()
        _out(f"  {color}{BOLD}Action:{RESET} {color}{action}{RESET}")

    _out()

    summaries = {
        "ok": f"{GREEN}{BOLD}✓  Printer is healthy." f" No replacements needed.{RESET}",
        "info": f"{CYAN}{BOLD}i  Printer is busy/processing."
        f" No replacements needed.{RESET}",
        "warn": f"{YELLOW}{BOLD}⚡ WARNING: Maintenance will be needed"
        f" soon.{RESET}\n{YELLOW}   Order replacement parts"
        f" now to avoid interruption.{RESET}",
        "critical": f"{RED}{BOLD}⚠  ACTION REQUIRED: Replacement or fix"
        f" needed now!{RESET}",
    }
    _out(summaries.get(severity, ""))


# ── Display: USB results ────────────────────────────────────────────


def display_usb_results(result: USBResult) -> None:
    """Print a formatted report for USB PJL query results."""
    if result.error:
        _out(f"{RED}Error: {result.error}{RESET}")
        sys.exit(1)

    _display_report_header()
    _display_usb_device_info(result)
    _display_pjl_status(result)
    _out()
    _display_consumables_reference()


# ── Display: Network helpers ────────────────────────────────────────


@dataclass
class _SupplyStatus:
    """Processed supply level info for display."""

    color: str
    bar: str
    status_text: str
    warning: str
    needs_replacement: bool


def _process_supply_item(desc: str, max_val: int, level: int) -> _SupplyStatus:
    """Process a single supply item into display info."""
    pct = -1
    status_text = ""
    color = GREEN
    warning = ""
    needs_replacement = False

    if level == SNMP_LEVEL_OK:
        status_text = "OK"
    elif level == SNMP_LEVEL_LOW:
        status_text = "LOW"
        color = RED
        needs_replacement = True
        warning = f"{desc} is LOW."
    elif level == 0:
        status_text = "EMPTY"
        color = RED
        pct = 0
        needs_replacement = True
        warning = f"{desc} is EMPTY -- replace now!"
    elif max_val > 0:
        pct = min(level * 100 // max_val, 100)
        status_text = f"{pct}%"
        if pct <= SUPPLY_LOW_PCT:
            color = RED
            needs_replacement = True
            warning = f"{desc} at {pct}%."
        elif pct <= SUPPLY_WARN_PCT:
            color = YELLOW
            warning = f"{desc} at {pct}% -- order soon."

    bar = ""
    if pct >= 0:
        filled = pct * PROGRESS_BAR_WIDTH // 100
        empty = PROGRESS_BAR_WIDTH - filled
        bar = f"[{'█' * filled}{'░' * empty}]"

    return _SupplyStatus(color, bar, status_text, warning, needs_replacement)


def _display_supply_warnings(*, needs_replacement: bool, warnings: list[str]) -> None:
    """Display supply level warnings summary."""
    _out()
    if needs_replacement:
        _out(f"{RED}{BOLD}⚠  ACTION NEEDED:{RESET}")
        for w in warnings:
            _out(f"   {RED}• {w}{RESET}")
    elif warnings:
        _out(f"{YELLOW}{BOLD}⚡ HEADS UP:{RESET}")
        for w in warnings:
            _out(f"   {YELLOW}• {w}{RESET}")
    else:
        _out(f"{GREEN}{BOLD}✓  All consumables are at healthy levels.{RESET}")


def _display_supply_levels(result: NetworkResult) -> None:
    """Display consumable supply levels section."""
    _out()
    _out(f"{BOLD}── Consumable Levels ──{RESET}")
    _out()

    needs_replacement = False
    warnings: list[str] = []

    for i, desc in enumerate(result.supply_descriptions):
        try:
            max_val = int(result.supply_max[i])
        except (IndexError, ValueError):
            max_val = 0
        try:
            level = int(result.supply_levels[i])
        except (IndexError, ValueError):
            level = 0

        item = _process_supply_item(desc, max_val, level)
        _out(
            f"  {BOLD}{desc:<25}{RESET}"
            f" {item.color}{item.bar} {item.status_text}{RESET}"
        )
        if item.needs_replacement:
            needs_replacement = True
        if item.warning:
            warnings.append(item.warning)

    _display_supply_warnings(needs_replacement=needs_replacement, warnings=warnings)


def _display_network_device_info(result: NetworkResult) -> None:
    """Display device info section for network results."""
    _out(f"{BOLD}Printer:{RESET}    {result.product or 'Unknown'}")
    _out(f"{BOLD}Connection:{RESET} Network ({result.ip})")
    if result.serial:
        _out(f"{BOLD}Serial:{RESET}     {result.serial}")
    if result.display:
        _out(f"{BOLD}Display:{RESET}    {result.display}")
    if result.page_count and result.page_count.isdigit():
        _out(f"{BOLD}Pages:{RESET}      {result.page_count} total")


# ── Display: Network results ────────────────────────────────────────


def display_network_results(result: NetworkResult) -> None:
    """Print a formatted report for SNMP network query results."""
    if result.error:
        _out(f"{RED}Error: {result.error}{RESET}")
        sys.exit(1)

    _display_report_header()
    _display_network_device_info(result)
    _display_supply_levels(result)

    _out()
    _out(
        f"{CYAN}Tip: Visit http://{result.ip} for the full web management"
        f" interface.{RESET}"
    )
    _out()


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


def main(argv: list[str] | None = None) -> None:
    """Entry point: auto-detect USB or network Brother printer."""
    args = argv if argv is not None else sys.argv[1:]
    printer_ip = args[0] if args else ""

    # ── Network mode (explicit IP given) ─────────────────────────
    if printer_ip:
        if not shutil.which("snmpwalk"):
            _out(
                f"{RED}snmpwalk not found." f" Install: sudo pacman -S net-snmp{RESET}"
            )
            sys.exit(1)
        _out(f"{CYAN}Querying printer at {printer_ip} via SNMP...{RESET}")
        net_result = query_network_snmp(printer_ip)
        display_network_results(net_result)
        return

    # ── Auto-detect: USB first, then network ─────────────────────
    usb_line = find_brother_usb()

    if usb_line:
        _out(f"{CYAN}Found Brother printer on USB: {usb_line}{RESET}")

        if os.geteuid() != 0:
            _out(
                f"{RED}Root access required for USB printer."
                f" Re-run with sudo.{RESET}"
            )
            sys.exit(1)

        usb_result = query_usb_pjl()
        display_usb_results(usb_result)
        return

    # ── Try network discovery via CUPS ───────────────────────────
    network_ip = _discover_network_printer()

    if network_ip and shutil.which("snmpwalk"):
        _out(f"{CYAN}Found network printer at {network_ip}{RESET}")
        net_result = query_network_snmp(network_ip)
        display_network_results(net_result)
        return

    _out(f"{RED}No Brother printer found.{RESET}")
    _out()
    _out("Ensure the printer is:")
    _out("  • Powered on")
    _out("  • Connected via USB or on the same network")
    _out()
    _out("Usage: python3 -m brother_printer [printer_ip]")
    sys.exit(1)


if __name__ == "__main__":
    main()

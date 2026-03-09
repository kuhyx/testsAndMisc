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
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import fcntl
import json
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

# Brother HL-1110 consumable page ratings
TONER_RATED_PAGES = 1000
DRUM_RATED_PAGES = 10000
CUPS_PAGE_LOG = Path("/var/log/cups/page_log")
CONSUMABLE_STATE_FILE = Path.home() / ".config" / "brother_printer" / "state.json"


def _out(text: str = "") -> None:
    """Write a line to stdout."""
    sys.stdout.write(text + "\n")


def _prompt(text: str) -> str:
    """Read user input with a prompt."""
    sys.stdout.write(text)
    sys.stdout.flush()
    return sys.stdin.readline().strip()


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
        "The toner cartridge needs immediate replacement (TN-1050/TN-1030 compatible).",
    ),
    40310: (
        "critical",
        "Toner End",
        "The toner cartridge is empty. Replace now (TN-1050/TN-1030 compatible).",
    ),
    # Drum
    30201: (
        "warn",
        "Drum End Soon",
        "The drum unit is nearing end of life. Order replacement (DR-1050 compatible).",
    ),
    40201: (
        "warn",
        "Drum End Soon",
        "The drum unit is nearing end of life. Order replacement (DR-1050 compatible).",
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
class CUPSJob:
    """A single CUPS print job."""

    job_id: str
    user: str
    size: str
    date: str


@dataclass
class CUPSQueueStatus:
    """Status of the CUPS print queue for a printer."""

    printer_name: str = ""
    enabled: bool = True
    reason: str = ""
    jobs: list[CUPSJob] = field(default_factory=list)
    has_backend_errors: bool = False
    last_backend_error: str = ""


@dataclass
class PageCountEstimate:
    """Estimated consumable life based on CUPS page count."""

    total_pages: int = 0
    toner_pages: int = 0
    drum_pages: int = 0
    toner_pct_remaining: int = 100
    drum_pct_remaining: int = 100
    toner_exhausted: bool = False
    toner_low: bool = False
    drum_near_end: bool = False


@dataclass
class USBPortStatus:
    """IEEE 1284 USB printer port status bits."""

    paper_empty: bool = False
    online: bool = True
    error: bool = False
    raw_byte: int = 0


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
    port_status: USBPortStatus | None = None


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


def _parse_cups_usb_uri(uri: str, info: dict[str, str]) -> None:
    """Extract product and serial from a CUPS usb:// URI."""
    parsed = urllib.parse.urlparse(uri)
    info["product"] = urllib.parse.unquote(parsed.path.lstrip("/"))
    qs = urllib.parse.parse_qs(parsed.query)
    if "serial" in qs:
        info["serial"] = qs["serial"][0]


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
            if "Brother" in line:
                for part in line.split():
                    if part.startswith("usb://"):
                        _parse_cups_usb_uri(part, info)
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


def _read_nonblocking(fd: int, flags: int) -> bytes:
    """Read all available data from fd in non-blocking mode."""
    data = b""
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    with contextlib.suppress(OSError):
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            data += chunk
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
    return data


def _wait_for_pjl_response(fd: int, flags: int, deadline: float) -> bytes:
    """Poll fd until PJL data arrives or deadline expires."""
    response = b""
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        readable, _, _ = select.select([fd], [], [], min(remaining, 1.0))
        if readable:
            response += _read_nonblocking(fd, flags)
            if response and (b"=" in response or b"@PJL" in response):
                break
    return response


def pjl_query(fd: int, cmd: str, timeout_sec: float = 5.0) -> str:
    """Send a PJL command via raw fd and read the response."""
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)

    pjl_cmd = f"\x1b%-12345X@PJL\r\n{cmd}\r\n\x1b%-12345X"
    os.write(fd, pjl_cmd.encode())

    deadline = time.time() + timeout_sec
    response = _wait_for_pjl_response(fd, flags, deadline)

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


def _run_pjl_queries(fd: int, result: USBResult, max_retries: int) -> None:
    """Execute PJL query sequence on an open file descriptor."""
    _drain_buffer(fd)

    os.write(fd, b"\x1b%-12345X@PJL\r\n\x1b%-12345X")
    time.sleep(0.5)
    _drain_buffer(fd)

    _retry_pjl_query(fd, "@PJL INFO STATUS", _parse_status, result, max_retries)
    _drain_buffer(fd)
    time.sleep(0.5)
    _retry_pjl_query(fd, "@PJL INFO VARIABLES", _parse_variables, result, max_retries)


def _init_usb_result(dev_path: str) -> USBResult:
    """Create a USBResult with device info from CUPS."""
    cups_info = get_printer_info_from_cups()
    return USBResult(
        device=dev_path,
        product=cups_info.get("product") or "Brother Laser Printer",
        serial=cups_info.get("serial", ""),
    )


def query_usb_pjl(max_retries: int = 2) -> USBResult:
    """Query a Brother printer via PJL over /dev/usb/lp*."""
    dev_path = find_usb_printer_dev()
    if not dev_path:
        return _query_usb_via_cups()

    result = _init_usb_result(dev_path)
    if not os.access(dev_path, os.R_OK | os.W_OK):
        result.error = f"Permission denied: {dev_path}. Run with sudo."
        return result

    fd: int | None = None
    try:
        fd = os.open(dev_path, os.O_RDWR)
        fcntl.fcntl(fd, fcntl.F_GETFL)
        _run_pjl_queries(fd, result, max_retries)
    except OSError as e:
        result.error = str(e)
    finally:
        if fd is not None:
            os.close(fd)
    return result


# ── CUPS-based USB fallback ──────────────────────────────────────────
# When the usblp kernel module is not available, /dev/usb/lp* devices
# don't exist even though CUPS can print fine via its own libusb backend.
# These functions query printer status through CUPS IPP instead.

_CUPS_REASONS_TO_STATUS: dict[str, int] = {
    "paused": 10023,
    "moving-to-paused": 10023,
    "toner-low": 30010,
    "toner-empty": 40310,
    "marker-supply-low": 30010,
    "marker-supply-empty": 40310,
    "media-empty": 40302,
    "media-needed": 40302,
    "media-jam": 40000,
    "cover-open": 41000,
    "door-open": 41000,
    "input-tray-missing": 40300,
}

_CUPS_STATE_TO_STATUS: dict[str, int] = {
    "idle": 10001,
    "processing": 10007,
    "stopped": 10023,
}


BROTHER_USB_VENDOR_ID = 0x04F9


def _get_pyusb_device_info() -> dict[str, str]:
    """Get Brother USB printer info via pyusb (no interface claim needed)."""
    try:
        import usb.core

        dev = usb.core.find(idVendor=BROTHER_USB_VENDOR_ID)
        if dev is None:
            return {}
    except Exception:  # noqa: BLE001
        return {}
    else:
        return {
            "product": dev.product or "",
            "serial": dev.serial_number or "",
        }


def _stop_cups() -> bool:
    """Stop CUPS service and sockets. Returns True on success."""
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return False
    try:
        subprocess.run(
            [systemctl, "stop", "cups.service", "cups.socket", "cups.path"],
            timeout=15,
            check=True,
        )
        time.sleep(2)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return False
    return True


def _is_cups_scheduler_running() -> bool:
    """Check if the CUPS scheduler is currently running."""
    lpstat = shutil.which("lpstat")
    if not lpstat:
        return False
    try:
        r = subprocess.run(
            [lpstat, "-r"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return (
            "is running" in r.stdout.lower() and "not running" not in r.stdout.lower()
        )
    except (subprocess.TimeoutExpired, OSError):
        return False


def _start_cups() -> bool:
    """Start CUPS service, socket, and path units. Returns True on success."""
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return False
    try:
        subprocess.run(
            [systemctl, "start", "cups.service", "cups.socket", "cups.path"],
            timeout=15,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return False
    # Verify CUPS is actually responding
    for _ in range(10):
        if _is_cups_scheduler_running():
            return True
        time.sleep(1)
    return False


def _query_usb_port_status_raw() -> USBPortStatus | None:
    """Query USB printer port status via pyusb control transfer.

    Requires root and temporarily stops CUPS to access the USB device.
    Returns None if the query fails.
    """
    try:
        import usb.core
        import usb.util
    except ImportError:
        return None

    dev = usb.core.find(idVendor=BROTHER_USB_VENDOR_ID)
    if dev is None:
        return None

    if not _stop_cups():
        return None

    try:
        dev.reset()
        time.sleep(2)
        dev = usb.core.find(idVendor=BROTHER_USB_VENDOR_ID)
        if dev is None:
            return None

        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except (usb.core.USBError, NotImplementedError):
            pass

        usb.util.claim_interface(dev, 0)
        try:
            # USB Printer Class GET_PORT_STATUS (bRequest=0x01)
            raw = dev.ctrl_transfer(0xA1, 0x01, 0, 0, 1, timeout=5000)
            port_byte = raw[0]
            return USBPortStatus(
                paper_empty=bool(port_byte & 0x20),
                online=bool(port_byte & 0x10),
                error=not bool(port_byte & 0x08),
                raw_byte=port_byte,
            )
        finally:
            usb.util.release_interface(dev, 0)
            usb.util.dispose_resources(dev)
    except Exception:  # noqa: BLE001
        logger.debug("USB port status query failed", exc_info=True)
        return None
    finally:
        _start_cups()


def _get_cups_total_pages() -> int:
    """Parse CUPS page_log to get total pages printed (deduplicated by job)."""
    if not CUPS_PAGE_LOG.exists():
        return 0
    try:
        text = CUPS_PAGE_LOG.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    # page_log format: printer user job_id [date] total N ...
    # Deduplicate by job_id (retries produce repeated lines)
    jobs: dict[str, int] = {}
    for line in text.splitlines():
        match = re.search(r"\s(\d+)\s+\[.*?\]\s+total\s+(\d+)", line)
        if match:
            job_id = match.group(1)
            pages = int(match.group(2))
            jobs[job_id] = max(jobs.get(job_id, 0), pages)
    return sum(jobs.values())


def _load_consumable_state() -> dict[str, int]:
    """Load consumable replacement state from disk.

    Returns dict with keys 'toner_replaced_at' and 'drum_replaced_at'
    (page counts when each consumable was last replaced).
    """
    defaults: dict[str, int] = {"toner_replaced_at": 0, "drum_replaced_at": 0}
    if not CONSUMABLE_STATE_FILE.exists():
        return defaults
    try:
        data = json.loads(
            CONSUMABLE_STATE_FILE.read_text(encoding="utf-8"),
        )
        return {
            "toner_replaced_at": int(data.get("toner_replaced_at", 0)),
            "drum_replaced_at": int(data.get("drum_replaced_at", 0)),
        }
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return defaults


def _save_consumable_state(state: dict[str, int]) -> None:
    """Persist consumable replacement state to disk."""
    CONSUMABLE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONSUMABLE_STATE_FILE.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )


def _reset_consumable(name: str) -> None:
    """Record current page count as replacement point for a consumable."""
    total = _get_cups_total_pages()
    state = _load_consumable_state()
    key = f"{name}_replaced_at"
    state[key] = total
    _save_consumable_state(state)
    _out(
        f"{GREEN}✓ {name.capitalize()} counter reset at page count" f" {total}.{RESET}"
    )
    _out(f"  State saved to {CONSUMABLE_STATE_FILE}")


def _estimate_consumable_life() -> PageCountEstimate:
    """Estimate toner/drum life from CUPS page count since last replacement."""
    total = _get_cups_total_pages()
    if total <= 0:
        return PageCountEstimate()
    state = _load_consumable_state()
    toner_pages = max(0, total - state["toner_replaced_at"])
    drum_pages = max(0, total - state["drum_replaced_at"])
    toner_pct = max(0, 100 - (toner_pages * 100 // TONER_RATED_PAGES))
    drum_pct = max(0, 100 - (drum_pages * 100 // DRUM_RATED_PAGES))
    return PageCountEstimate(
        total_pages=total,
        toner_pages=toner_pages,
        drum_pages=drum_pages,
        toner_pct_remaining=toner_pct,
        drum_pct_remaining=drum_pct,
        toner_exhausted=toner_pages >= TONER_RATED_PAGES,
        toner_low=toner_pages >= TONER_RATED_PAGES * 80 // 100,
        drum_near_end=drum_pages >= DRUM_RATED_PAGES * 90 // 100,
    )


def _parse_ipp_attributes(output: str) -> dict[str, str]:
    """Parse ipptool verbose output into an attribute dict."""
    attrs: dict[str, str] = {}
    for line in output.splitlines():
        match = re.match(r"\s+(\S+)\s+\([^)]+\)\s+=\s+(.*)", line)
        if match:
            attrs[match.group(1)] = match.group(2).strip()
    return attrs


def _get_cups_ipp_status(printer_name: str) -> dict[str, str]:
    """Query printer attributes via CUPS IPP using ipptool."""
    ipptool_path = shutil.which("ipptool")
    if not ipptool_path:
        return {}
    uri = f"ipp://localhost/printers/{printer_name}"
    try:
        r = subprocess.run(
            [ipptool_path, "-tv", uri, "get-printer-attributes.test"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return _parse_ipp_attributes(r.stdout)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return {}


def _get_cups_economode(printer_name: str) -> str:
    """Query toner save mode setting via lpoptions."""
    lpoptions_path = shutil.which("lpoptions")
    if not lpoptions_path:
        return ""
    try:
        r = subprocess.run(
            [lpoptions_path, "-p", printer_name, "-l"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if "conomode" in line.lower():
                match = re.search(r"\*(\w+)", line)
                if match:
                    return "ON" if match.group(1).lower() == "true" else "OFF"
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass
    return ""


def _map_cups_to_status_code(state: str, reasons: str) -> str:
    """Map CUPS state + reasons to a Brother PJL status code string."""
    for keyword, code in _CUPS_REASONS_TO_STATUS.items():
        if keyword in reasons.lower():
            return str(code)
    clean_state = re.sub(r"\(.*\)", "", state).strip().lower()
    return str(_CUPS_STATE_TO_STATUS.get(clean_state, 10001))


_ERROR_REASON_MAP: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("media-jam",), "40000", "Paper Jam"),
    (("cover-open", "door-open"), "41000", "Cover Open"),
    (("toner-empty",), "40310", "Toner End"),
    (("toner-low",), "30010", "Toner Low"),
)


def _cups_reasons_to_error(cups_reasons: str) -> tuple[str, str]:
    """Map CUPS reason keywords to a (status_code, display) pair."""
    reasons_lower = cups_reasons.lower()
    for keywords, code, display in _ERROR_REASON_MAP:
        if any(kw in reasons_lower for kw in keywords):
            return code, display
    return "42000", "Printer Error"


def _port_status_to_status_code(
    ps: USBPortStatus,
    cups_reasons: str,
) -> tuple[str, str]:
    """Map USB port status + CUPS reasons to (status_code, display)."""
    # Hardware error flags take priority
    if ps.error and ps.paper_empty:
        return "40302", "No Paper"
    if ps.error and not ps.online:
        return "41000", "Cover Open"
    if ps.error:
        return _cups_reasons_to_error(cups_reasons)
    if ps.paper_empty:
        return "40302", "No Paper"
    if not ps.online:
        return "10002", "Offline / Sleep"
    return "", ""


def _ensure_cups_running() -> bool:
    """Make sure CUPS is running, starting it if necessary."""
    if _is_cups_scheduler_running():
        return True
    return _start_cups()


def _query_usb_via_cups() -> USBResult:
    """Query USB printer status through CUPS when /dev/usb/lp* is unavailable."""
    _ensure_cups_running()
    printer_name = _find_cups_printer_name()
    if not printer_name:
        return USBResult(
            error="No USB printer device at /dev/usb/lp*"
            " (usblp module not available)"
            " and no Brother printer found in CUPS.",
        )

    pyusb_info = _get_pyusb_device_info()
    cups_info = get_printer_info_from_cups()

    result = USBResult(
        device="cups",
        product=(
            pyusb_info.get("product")
            or cups_info.get("product")
            or "Brother Laser Printer"
        ),
        serial=pyusb_info.get("serial") or cups_info.get("serial", ""),
    )

    ipp = _get_cups_ipp_status(printer_name)
    state = ipp.get("printer-state", "")
    reasons = ipp.get("printer-state-reasons", "none")
    result.economode = _get_cups_economode(printer_name)

    # Direct USB hardware status query
    port_status = _query_usb_port_status_raw()
    if port_status is not None:
        result.port_status = port_status
        hw_code, hw_display = _port_status_to_status_code(
            port_status,
            reasons,
        )
        if hw_code:
            result.status_code = hw_code
            result.display = hw_display
            result.online = "TRUE" if port_status.online else "FALSE"
            return result
        # Hardware says OK — check page count for toner/drum warnings
        estimate = _estimate_consumable_life()
        if estimate.toner_exhausted:
            result.status_code = "40310"
            result.display = "Toner End (estimated from page count)"
            result.online = "TRUE"
            return result
        if estimate.toner_low:
            result.status_code = "30010"
            result.display = "Toner Low (estimated from page count)"
            result.online = "TRUE"
            return result
        result.status_code = _map_cups_to_status_code(state, reasons)
        result.display = ipp.get("printer-state-message", "")
        result.online = "TRUE"
        return result

    # pyusb unavailable: CUPS-only fallback
    result.status_code = _map_cups_to_status_code(state, reasons)
    result.display = ipp.get("printer-state-message", "")
    result.online = "TRUE" if state.lower() in {"idle", "processing"} else "FALSE"

    return result


# ── SNMP network query ──────────────────────────────────────────────


def _snmpwalk_cmd(
    path: str, community: str, timeout: int, ip: str, oid: str
) -> list[str]:
    """Build the snmpwalk command arguments."""
    return [path, "-v", "2c", "-c", community, "-t", str(timeout), "-OQvs", ip, oid]


def snmp_walk(ip: str, oid: str, community: str, timeout: int) -> list[str]:
    """Run snmpwalk and return cleaned values."""
    snmpwalk_path = shutil.which("snmpwalk")
    if not snmpwalk_path:
        return []
    try:
        r = subprocess.run(
            _snmpwalk_cmd(snmpwalk_path, community, timeout, ip, oid),
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


def _snmpget_cmd(
    path: str, community: str, timeout: int, ip: str, oid: str
) -> list[str]:
    """Build the snmpget command arguments."""
    return [path, "-v", "2c", "-c", community, "-t", str(timeout), ip, oid]


def _check_snmp_connectivity(ip: str, community: str, timeout: int) -> str | None:
    """Verify SNMP connectivity. Returns error message or None on success."""
    snmpget_path = shutil.which("snmpget")
    if not snmpget_path:
        return "snmpget not found. Install: sudo pacman -S net-snmp"
    try:
        subprocess.run(
            _snmpget_cmd(
                snmpget_path,
                community,
                timeout,
                ip,
                "1.3.6.1.2.1.43.11.1.1.6.1.1",
            ),
            capture_output=True,
            timeout=10,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return f"Cannot reach printer at {ip} via SNMP."
    return None


def _build_network_result(ip: str, community: str, timeout: int) -> NetworkResult:
    """Collect all SNMP data into a NetworkResult."""

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


def query_network_snmp(ip: str) -> NetworkResult:
    """Query a Brother printer via SNMP over the network."""
    community = "public"
    timeout = 5
    error = _check_snmp_connectivity(ip, community, timeout)
    if error:
        return NetworkResult(ip=ip, error=error)
    return _build_network_result(ip, community, timeout)


# ── CUPS queue inspection ────────────────────────────────────────────


def _find_cups_printer_name() -> str:
    """Find the CUPS queue name for a Brother printer."""
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
        for line in r.stdout.splitlines():
            if "brother" in line.lower():
                # e.g. device for Brother_HL-1110_series: usb://...
                match = re.match(r"device for (\S+):", line)
                if match:
                    return match.group(1)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass
    return ""


def _parse_lpstat_printer_line(line: str) -> tuple[bool, str]:
    """Parse an lpstat -p line. Returns (enabled, reason)."""
    enabled = "disabled" not in line.lower()
    reason = ""
    # Reason follows the dash after the date
    match = re.search(r"\d{4}\s+-\s*(.+)", line)
    if match:
        reason = match.group(1).strip()
    return enabled, reason


def _parse_lpstat_jobs(output: str, printer_name: str) -> list[CUPSJob]:
    """Parse lpstat -o output into CUPSJob list."""
    jobs: list[CUPSJob] = []
    for line in output.splitlines():
        if not line.startswith(printer_name):
            continue
        parts = line.split()
        if len(parts) >= 4:  # noqa: PLR2004
            job_id = parts[0]
            user = parts[1]
            size = parts[2]
            date = " ".join(parts[3:])
            jobs.append(CUPSJob(job_id=job_id, user=user, size=size, date=date))
    return jobs


def get_cups_queue_status() -> CUPSQueueStatus:
    """Check if the CUPS queue is disabled and list pending jobs."""
    printer_name = _find_cups_printer_name()
    if not printer_name:
        return CUPSQueueStatus()

    result = CUPSQueueStatus(printer_name=printer_name)
    lpstat_path = shutil.which("lpstat")
    if not lpstat_path:
        return result

    # Check printer enabled/disabled state
    try:
        r = subprocess.run(
            [lpstat_path, "-p", printer_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if "printer" in line.lower() and printer_name in line:
                result.enabled, result.reason = _parse_lpstat_printer_line(line)
                break
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass

    # List pending jobs
    try:
        r = subprocess.run(
            [lpstat_path, "-o", printer_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        result.jobs = _parse_lpstat_jobs(r.stdout, printer_name)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass

    # Check for stale backend errors
    has_errors, last_error = _check_cups_backend_errors(printer_name)
    result.has_backend_errors = has_errors
    result.last_backend_error = last_error

    return result


def _cups_enable_printer(printer_name: str) -> bool:
    """Re-enable a disabled CUPS printer. Returns True on success."""
    cupsenable_path = shutil.which("cupsenable")
    if not cupsenable_path:
        _out(f"  {RED}cupsenable not found.{RESET}")
        return False
    try:
        subprocess.run(
            [cupsenable_path, printer_name],
            timeout=5,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
        _out(f"  {RED}Failed to enable printer: {e}{RESET}")
        return False
    else:
        return True


def _cups_cancel_all_jobs(printer_name: str) -> bool:
    """Cancel all pending jobs. Returns True on success."""
    cancel_path = shutil.which("cancel")
    if not cancel_path:
        _out(f"  {RED}cancel command not found.{RESET}")
        return False
    try:
        subprocess.run(
            [cancel_path, "-a", printer_name],
            timeout=5,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
        _out(f"  {RED}Failed to cancel jobs: {e}{RESET}")
        return False
    else:
        return True


def _cups_cancel_job(job_id: str) -> bool:
    """Cancel a specific job. Returns True on success."""
    cancel_path = shutil.which("cancel")
    if not cancel_path:
        return False
    try:
        subprocess.run(
            [cancel_path, job_id],
            timeout=5,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return False
    else:
        return True


def _cups_restart_service() -> bool:
    """Restart the CUPS service. Returns True on success."""
    systemctl_path = shutil.which("systemctl")
    if not systemctl_path:
        _out(f"  {RED}systemctl not found.{RESET}")
        return False
    sys.stdout.write(f"  {DIM}Restarting CUPS...{RESET}")
    sys.stdout.flush()
    try:
        proc = subprocess.Popen(
            [systemctl_path, "restart", "cups"],
        )
        deadline = time.time() + 30
        while proc.poll() is None:
            if time.time() > deadline:
                proc.kill()
                proc.wait()
                sys.stdout.write("\n")
                _out(
                    f"  {RED}CUPS restart timed out"
                    f" (stuck backend process?).{RESET}"
                )
                _out(
                    f"  {DIM}Try: sudo kill -9 $(pgrep -f 'cups/backend/usb')"
                    f" && sudo systemctl restart cups{RESET}"
                )
                return False
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\n")
        if proc.returncode != 0:
            _out(
                f"  {RED}CUPS restart failed" f" (exit code {proc.returncode}).{RESET}"
            )
            return False
    except OSError as e:
        sys.stdout.write("\n")
        _out(f"  {RED}Failed to restart CUPS: {e}{RESET}")
        return False
    time.sleep(2)  # wait for CUPS to come back up
    return True


def _is_cups_printer_healthy(printer_name: str) -> bool:
    """Check live CUPS state via lpstat. Returns True if enabled with no issues."""
    lpstat_path = shutil.which("lpstat")
    if not lpstat_path:
        return False
    try:
        r = subprocess.run(
            [lpstat_path, "-p", printer_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if (
                printer_name in line
                and "idle" in line.lower()
                and "enabled" in line.lower()
            ):
                return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass
    return False


def _find_backend_error_in_log(
    lines: list[str],
) -> tuple[str, str, str]:
    """Scan CUPS log lines (reversed) for backend errors.

    Returns:
        (backend_error, error_timestamp, last_success_timestamp)
    """
    backend_error = ""
    error_timestamp = ""
    last_success_timestamp = ""

    for line in reversed(lines):
        if (
            "backend errors" in line or "stopped with status" in line
        ) and not backend_error:
            backend_error = line.strip()
            ts_match = re.search(r"\[([^\]]+)\]", line)
            if ts_match:
                error_timestamp = ts_match.group(1)
        # Check if a job completed successfully after the error
        if ("Completed" in line or "total" in line) and error_timestamp:
            ts_match = re.search(r"\[([^\]]+)\]", line)
            if ts_match:
                last_success_timestamp = ts_match.group(1)
                break

    return backend_error, error_timestamp, last_success_timestamp


def _check_cups_backend_errors(
    printer_name: str,
) -> tuple[bool, str]:
    """Check CUPS error log for backend errors. Returns (has_errors, last_error)."""
    # If the printer is currently healthy, ignore stale log entries.
    if _is_cups_printer_healthy(printer_name):
        return False, ""

    log_path = Path("/var/log/cups/error_log")
    if not log_path.exists():
        return False, ""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False, ""

    backend_error, error_timestamp, last_success_timestamp = _find_backend_error_in_log(
        lines
    )

    if not backend_error:
        return False, ""

    # If there's been a successful print after the error, backend is fine
    if last_success_timestamp and last_success_timestamp > error_timestamp:
        return False, ""

    return True, backend_error


def _display_cups_queue_status(queue: CUPSQueueStatus) -> None:
    """Display CUPS queue status and offer interactive fixes."""
    if not queue.printer_name:
        return
    if queue.enabled and not queue.jobs and not queue.has_backend_errors:
        return

    _out()
    _out(f"{BOLD}── Print Queue ──{RESET}")
    _out()

    if queue.has_backend_errors and queue.enabled and not queue.jobs:
        _out(f"  {YELLOW}{BOLD}⚡ CUPS backend has stale errors{RESET}")
        _out(
            f"  {DIM}New print jobs may silently fail."
            f" A CUPS restart usually fixes this.{RESET}"
        )
        _out()

    if not queue.enabled:
        _out(f"  {RED}{BOLD}⚠  Printer queue is DISABLED{RESET}")
        if queue.reason:
            _out(f"  {DIM}Reason: {queue.reason}{RESET}")
        _out()

    if queue.jobs:
        _out(f"  {BOLD}Pending jobs ({len(queue.jobs)}):{RESET}")
        for job in queue.jobs:
            _out(f"    {job.job_id}  {DIM}{job.user}  {job.size}B  {job.date}{RESET}")
        _out()

    _offer_queue_fix(queue)


def _offer_queue_fix(queue: CUPSQueueStatus) -> None:
    """Prompt the user to fix a disabled queue / pending jobs."""
    _out(f"  {BOLD}Available actions:{RESET}")

    options: list[str] = []
    if not queue.enabled and queue.jobs:
        _out(f"    {CYAN}1){RESET} Re-enable printer and retry all jobs")
        _out(f"    {CYAN}2){RESET} Re-enable printer and cancel all jobs")
        _out(f"    {CYAN}3){RESET} Cancel all jobs (keep printer disabled)")
        _out(f"    {CYAN}4){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}5){RESET} Restart CUPS + re-enable + retry all jobs")
        _out(f"    {CYAN}6){RESET} Do nothing")
        options = ["1", "2", "3", "4", "5", "6"]
    elif not queue.enabled:
        _out(f"    {CYAN}1){RESET} Re-enable printer")
        _out(f"    {CYAN}2){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}3){RESET} Do nothing")
        options = ["1", "2", "3"]
    elif queue.jobs:
        _out(f"    {CYAN}1){RESET} Cancel all pending jobs")
        _out(f"    {CYAN}2){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}3){RESET} Do nothing")
        options = ["1", "2", "3"]
    else:
        # Backend errors only, printer enabled, no jobs
        _out(f"    {CYAN}1){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}2){RESET} Do nothing")
        options = ["1", "2"]

    _out()
    choice = _prompt(f"  Choose [{'/'.join(options)}]: ")
    _out()

    if not queue.enabled and queue.jobs:
        _handle_disabled_with_jobs(queue, choice)
    elif not queue.enabled:
        _handle_disabled_no_jobs(queue, choice)
    elif queue.jobs:
        _handle_enabled_with_jobs(queue, choice)
    else:
        _handle_backend_errors_only(choice)


def _handle_disabled_with_jobs(queue: CUPSQueueStatus, choice: str) -> None:  # noqa: C901
    """Handle fix for disabled printer with pending jobs."""
    if choice == "1":
        if _cups_enable_printer(queue.printer_name):
            _out(f"  {GREEN}✓ Printer re-enabled. Jobs will be retried.{RESET}")
    elif choice == "2":
        _cups_cancel_all_jobs(queue.printer_name)
        if _cups_enable_printer(queue.printer_name):
            _out(f"  {GREEN}✓ All jobs cancelled and printer re-enabled.{RESET}")
    elif choice == "3":
        if _cups_cancel_all_jobs(queue.printer_name):
            _out(f"  {GREEN}✓ All jobs cancelled.{RESET}")
    elif choice == "4":
        if _cups_restart_service():
            _out(f"  {GREEN}✓ CUPS restarted.{RESET}")
    elif choice == "5":
        if _cups_restart_service():
            _cups_enable_printer(queue.printer_name)
            _out(
                f"  {GREEN}✓ CUPS restarted, printer re-enabled."
                f" Jobs will be retried.{RESET}"
            )
    else:
        _out(f"  {DIM}No changes made.{RESET}")


def _handle_disabled_no_jobs(queue: CUPSQueueStatus, choice: str) -> None:
    """Handle fix for disabled printer with no pending jobs."""
    if choice == "1":
        if _cups_enable_printer(queue.printer_name):
            _out(f"  {GREEN}✓ Printer re-enabled.{RESET}")
    elif choice == "2":
        if _cups_restart_service():
            _cups_enable_printer(queue.printer_name)
            _out(f"  {GREEN}✓ CUPS restarted and printer re-enabled.{RESET}")
    else:
        _out(f"  {DIM}No changes made.{RESET}")


def _handle_enabled_with_jobs(queue: CUPSQueueStatus, choice: str) -> None:
    """Handle fix for enabled printer with stuck jobs."""
    if choice == "1":
        if _cups_cancel_all_jobs(queue.printer_name):
            _out(f"  {GREEN}✓ All jobs cancelled.{RESET}")
    elif choice == "2":
        if _cups_restart_service():
            _out(f"  {GREEN}✓ CUPS restarted.{RESET}")
    else:
        _out(f"  {DIM}No changes made.{RESET}")


def _handle_backend_errors_only(choice: str) -> None:
    """Handle fix when only stale backend errors are detected."""
    if choice == "1":
        if _cups_restart_service():
            _out(f"  {GREEN}✓ CUPS restarted. Stale backend errors cleared.{RESET}")
    else:
        _out(f"  {DIM}No changes made.{RESET}")


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


def _display_page_count_estimate() -> None:
    """Show estimated consumable life based on CUPS page count."""
    estimate = _estimate_consumable_life()
    if estimate.total_pages <= 0:
        return
    _out(f"{BOLD}── Page Count Estimate ──{RESET}")
    _out()
    _out(
        f"  {BOLD}Total pages printed:{RESET} {estimate.total_pages}"
        f"  (toner: {estimate.toner_pages} since replacement,"
        f" drum: {estimate.drum_pages} since replacement)"
    )
    _out()
    # Toner bar
    toner_pct = estimate.toner_pct_remaining
    toner_filled = toner_pct * PROGRESS_BAR_WIDTH // 100
    toner_empty = PROGRESS_BAR_WIDTH - toner_filled
    toner_bar = f"[{'█' * toner_filled}{'░' * toner_empty}]"
    if estimate.toner_exhausted:
        toner_color = RED
        toner_note = " ← REPLACE NOW"
    elif estimate.toner_low:
        toner_color = YELLOW
        toner_note = " ← order soon"
    else:
        toner_color = GREEN
        toner_note = ""
    _out(
        f"  {BOLD}Toner:{RESET} {toner_color}{toner_bar} ~{toner_pct}%"
        f"{toner_note}{RESET}"
    )
    # Drum bar
    drum_pct = estimate.drum_pct_remaining
    drum_filled = drum_pct * PROGRESS_BAR_WIDTH // 100
    drum_empty = PROGRESS_BAR_WIDTH - drum_filled
    drum_bar = f"[{'█' * drum_filled}{'░' * drum_empty}]"
    if estimate.drum_near_end:
        drum_color = YELLOW
        drum_note = " ← nearing end"
    else:
        drum_color = GREEN
        drum_note = ""
    _out(
        f"  {BOLD}Drum:{RESET}  {drum_color}{drum_bar} ~{drum_pct}%"
        f"{drum_note}{RESET}"
    )
    _out(
        f"  {DIM}Based on pages since last replacement"
        f" vs rated capacity (toner ~{TONER_RATED_PAGES},"
        f" drum ~{DRUM_RATED_PAGES}).{RESET}"
    )
    _out(f"  {DIM}Reset after replacing: --reset-toner" f" or --reset-drum{RESET}")
    if estimate.toner_exhausted:
        _out()
        _out(
            f"  {RED}{BOLD}⚠  Toner is likely exhausted."
            f" This is probably why the orange light is flashing.{RESET}"
        )
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


_SEVERITY_ICONS: dict[str, str] = {
    "ok": "✓",
    "info": "i",
    "warn": "⚡",
    "critical": "⚠",
}
_SEVERITY_COLORS: dict[str, str] = {
    "ok": GREEN,
    "info": CYAN,
    "warn": YELLOW,
    "critical": RED,
}
_SEVERITY_SUMMARIES: dict[str, str] = {
    "ok": f"{GREEN}{BOLD}✓  Printer is healthy. No replacements needed.{RESET}",
    "info": f"{CYAN}{BOLD}i  Printer is busy/processing."
    f" No replacements needed.{RESET}",
    "warn": f"{YELLOW}{BOLD}⚡ WARNING: Maintenance will be needed"
    f" soon.{RESET}\n{YELLOW}   Order replacement parts"
    f" now to avoid interruption.{RESET}",
    "critical": f"{RED}{BOLD}⚠  ACTION REQUIRED: Replacement or fix needed now!{RESET}",
}


def _format_status_detail(
    severity: str, short_text: str, action: str, result: USBResult
) -> None:
    """Print severity icon, display text, and action."""
    color = _SEVERITY_COLORS.get(severity, GREEN)
    icon = _SEVERITY_ICONS.get(severity, "✓")

    _out(f"  {color}{BOLD}{icon}  {short_text}{RESET}")
    if result.display and result.display != short_text:
        _out(f"  {DIM}Display: {result.display}{RESET}")
    _out(f"  {DIM}Status code: {result.status_code}{RESET}")

    if action:
        _out()
        _out(f"  {color}{BOLD}Action:{RESET} {color}{action}{RESET}")
    _out()
    _out(_SEVERITY_SUMMARIES.get(severity, ""))


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
    _format_status_detail(severity, short_text, action, result)


# ── Display: USB results ────────────────────────────────────────────


def _display_cups_fallback_note(result: USBResult) -> None:
    """Show a note when running in CUPS fallback mode."""
    _out()
    if result.port_status is not None:
        _out(
            f"  {DIM}Note: Hardware status obtained via USB port query."
            f" Toner/drum percentages not available.{RESET}"
        )
    else:
        _out(
            f"  {DIM}Note: pyusb not available; status obtained via"
            f" CUPS only. Detailed toner/drum levels are not"
            f" available in this mode.{RESET}"
        )


def display_usb_results(result: USBResult) -> None:
    """Print a formatted report for USB PJL query results."""
    if result.error:
        _out(f"{RED}Error: {result.error}{RESET}")
        sys.exit(1)

    _display_report_header()
    _display_usb_device_info(result)
    _display_pjl_status(result)

    if result.device == "cups":
        _display_cups_fallback_note(result)

    _out()
    _display_page_count_estimate()
    _display_consumables_reference()

    queue = get_cups_queue_status()
    _display_cups_queue_status(queue)


# ── Display: Network helpers ────────────────────────────────────────


@dataclass
class _SupplyStatus:
    """Processed supply level info for display."""

    color: str
    bar: str
    status_text: str
    warning: str
    needs_replacement: bool


def _classify_percentage_level(desc: str, pct: int) -> tuple[int, str, str, str, bool]:
    """Classify a supply by its calculated percentage."""
    if pct <= SUPPLY_LOW_PCT:
        return pct, f"{pct}%", RED, f"{desc} at {pct}%.", True
    if pct <= SUPPLY_WARN_PCT:
        return pct, f"{pct}%", YELLOW, f"{desc} at {pct}% -- order soon.", False
    return pct, f"{pct}%", GREEN, "", False


def _classify_supply_level(
    desc: str, max_val: int, level: int
) -> tuple[int, str, str, str, bool]:
    """Classify a supply level. Returns (pct, status, color, warning, replace)."""
    if level == SNMP_LEVEL_OK:
        return -1, "OK", GREEN, "", False
    if level == SNMP_LEVEL_LOW:
        return -1, "LOW", RED, f"{desc} is LOW.", True
    if level == 0:
        return 0, "EMPTY", RED, f"{desc} is EMPTY -- replace now!", True
    if max_val > 0:
        pct = min(level * 100 // max_val, 100)
        return _classify_percentage_level(desc, pct)
    return -1, "", GREEN, "", False


def _format_supply_bar(pct: int) -> str:
    """Build a progress bar string for a supply percentage."""
    if pct < 0:
        return ""
    filled = pct * PROGRESS_BAR_WIDTH // 100
    empty = PROGRESS_BAR_WIDTH - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _process_supply_item(desc: str, max_val: int, level: int) -> _SupplyStatus:
    """Process a single supply item into display info."""
    pct, status_text, color, warning, needs_replacement = _classify_supply_level(
        desc, max_val, level
    )
    bar = _format_supply_bar(pct)
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


def _parse_supply_value(values: list[str], index: int) -> int:
    """Safely parse an integer from a supply value list."""
    try:
        return int(values[index])
    except (IndexError, ValueError):
        return 0


def _collect_supply_items(
    result: NetworkResult,
) -> tuple[list[_SupplyStatus], list[str]]:
    """Parse and collect supply items with their descriptions."""
    items: list[_SupplyStatus] = []
    descs: list[str] = []
    for i, desc in enumerate(result.supply_descriptions):
        max_val = _parse_supply_value(result.supply_max, i)
        level = _parse_supply_value(result.supply_levels, i)
        items.append(_process_supply_item(desc, max_val, level))
        descs.append(desc)
    return items, descs


def _display_supply_levels(result: NetworkResult) -> None:
    """Display consumable supply levels section."""
    _out()
    _out(f"{BOLD}── Consumable Levels ──{RESET}")
    _out()

    needs_replacement = False
    warnings: list[str] = []
    items, descs = _collect_supply_items(result)

    for desc, item in zip(descs, items, strict=True):
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

    # Handle consumable reset commands
    if args and args[0] == "--reset-toner":
        _reset_consumable("toner")
        return
    if args and args[0] == "--reset-drum":
        _reset_consumable("drum")
        return

    # Enforce root — needed for USB hardware queries and CUPS management
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

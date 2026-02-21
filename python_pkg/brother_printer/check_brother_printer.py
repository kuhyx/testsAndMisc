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
        return USBResult(error="No USB printer device found at /dev/usb/lp*")

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
    try:
        subprocess.run(
            [systemctl_path, "restart", "cups"],
            timeout=15,
            check=True,
        )
        time.sleep(2)  # wait for CUPS to come back up
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
        _out(f"  {RED}Failed to restart CUPS: {e}{RESET}")
        return False
    else:
        return True


def _check_cups_backend_errors(
    printer_name: str,  # noqa: ARG001
) -> tuple[bool, str]:
    """Check CUPS error log for backend errors. Returns (has_errors, last_error)."""
    log_path = Path("/var/log/cups/error_log")
    if not log_path.exists():
        return False, ""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False, ""

    # Look for backend errors related to this printer (scan from end)
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
    if os.geteuid() != 0:
        _out(f"{RED}Root access required for USB printer. Re-run with sudo.{RESET}")
        sys.exit(1)
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

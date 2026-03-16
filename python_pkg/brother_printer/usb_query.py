"""USB printer discovery and PJL query functions."""

from __future__ import annotations

import contextlib
import fcntl
import os
from pathlib import Path
import select
import shutil
import subprocess
import time
from typing import TYPE_CHECKING
import urllib.parse

from python_pkg.brother_printer.data_classes import USBResult

if TYPE_CHECKING:
    from collections.abc import Callable

import logging

logger = logging.getLogger(__name__)


# ── USB printer discovery ────────────────────────────────────────────


def find_brother_usb() -> str:
    """Look for any Brother printer on USB via lsusb. Returns the info line."""
    if not shutil.which("lsusb"):
        return ""
    try:
        r = subprocess.run(
            ["/usr/bin/lsusb"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if "04f9:" in line.lower():
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
            ["/usr/bin/lpstat", "-v"],
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
        from python_pkg.brother_printer.cups_service import query_usb_via_cups

        return query_usb_via_cups()

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

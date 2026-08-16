"""USB printer discovery and PJL query functions.

The non-blocking PJL transport lives in _pjl_io.py. Its three entry points are
imported back here because tests/test_usb_query.py patches them on this module.
"""

from __future__ import annotations

import errno
import importlib
import logging
import os
from pathlib import Path
import shutil
import time
from typing import TYPE_CHECKING

from python_pkg.brother_printer._pjl_io import (
    _drain_buffer,
    _write_with_deadline,
    pjl_query,
)
from python_pkg.brother_printer._query import (
    printer_info_from_cups,
    run_command_text,
)
from python_pkg.brother_printer.data_classes import USBResult

if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


# ── USB printer discovery ────────────────────────────────────────────


def find_brother_usb() -> str:
    """Look for any Brother printer on USB via lsusb. Returns the info line."""
    if not shutil.which("lsusb"):
        return ""
    for line in run_command_text(["/usr/bin/lsusb"]).splitlines():
        if "04f9:" in line.lower():
            return line.split(": ", 1)[1] if ": " in line else line
    return ""


def find_usb_printer_dev() -> str | None:
    """Find /dev/usb/lp* device for the Brother printer."""
    devices = sorted(Path("/dev/usb").glob("lp*"))
    return str(devices[0]) if devices else None


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


def _parse_pagecount(resp: str, result: USBResult) -> bool:
    """Parse PAGECOUNT response into result. Returns True if a count was found."""
    for raw_line in resp.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("PAGECOUNT="):
            value = stripped.split("=", 1)[1].strip()
            if value.isdigit():
                result.page_count = value
                return True
    return False


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

    # Universal Exit Language, to drop the printer out of any language mode it
    # is in and have it listen for PJL. Deadline-bounded like every other write.
    _write_with_deadline(fd, b"\x1b%-12345X@PJL\r\n\x1b%-12345X", time.time() + 5.0)
    time.sleep(0.5)
    _drain_buffer(fd)

    _retry_pjl_query(fd, "@PJL INFO STATUS", _parse_status, result, max_retries)
    _drain_buffer(fd)
    time.sleep(0.5)
    _retry_pjl_query(fd, "@PJL INFO PAGECOUNT", _parse_pagecount, result, max_retries)
    _drain_buffer(fd)
    time.sleep(0.5)
    _retry_pjl_query(fd, "@PJL INFO VARIABLES", _parse_variables, result, max_retries)


def _init_usb_result(dev_path: str) -> USBResult:
    """Create a USBResult with device info from CUPS."""
    cups_info = printer_info_from_cups()
    return USBResult(
        device=dev_path,
        product=cups_info.get("product") or "Brother Laser Printer",
        serial=cups_info.get("serial", ""),
    )


def query_usb_pjl(max_retries: int = 2) -> USBResult:
    """Query a Brother printer via PJL over /dev/usb/lp*."""
    dev_path = find_usb_printer_dev()
    if not dev_path:
        cups_fallback = importlib.import_module(
            "python_pkg.brother_printer._cups_fallback",
        )
        return cups_fallback.query_usb_via_cups()

    result = _init_usb_result(dev_path)
    if not os.access(dev_path, os.R_OK | os.W_OK):
        result.error = f"Permission denied: {dev_path}. Run with sudo."
        return result

    fd: int | None = None
    try:
        # O_NONBLOCK or this open() hangs forever on an unwell printer.
        fd = os.open(dev_path, os.O_RDWR | os.O_NONBLOCK)
        _run_pjl_queries(fd, result, max_retries)
    except OSError as e:
        result.error = _describe_open_error(dev_path, e)
    finally:
        if fd is not None:
            os.close(fd)
    if not result.status_code and not result.error:
        result.error = (
            f"The printer did not answer PJL on {dev_path}. It is usually busy"
            " with a job, or wedged - power-cycle it if this persists."
        )
    return result


def _describe_open_error(dev_path: str, exc: OSError) -> str:
    """Turn an errno from opening the printer into something actionable."""
    if exc.errno == errno.EBUSY:
        return (
            f"{dev_path} is busy: another process (usually the CUPS backend"
            " mid-job) holds the printer. Wait for the job to finish."
        )
    if exc.errno == errno.EACCES:
        return f"Permission denied: {dev_path}. Run with sudo."
    return f"Could not read {dev_path}: {exc}"

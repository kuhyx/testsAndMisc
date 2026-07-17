"""CUPS service management, USB port status, and the CUPS-based fallback query.

Consumable life tracking lives in consumables.py.
"""

from __future__ import annotations

import contextlib
import fcntl
import importlib
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import TYPE_CHECKING

from python_pkg.brother_printer._query import (
    printer_info_from_cups,
    run_command_text,
)
from python_pkg.brother_printer.constants import (
    _CUPS_REASONS_TO_STATUS,
    _CUPS_STATE_TO_STATUS,
    _ERROR_REASON_MAP,
    BROTHER_USB_VENDOR_ID,
    DERIVED_CUPS_ERROR,
    DERIVED_TONER_END,
    DERIVED_TONER_LOW,
)
from python_pkg.brother_printer.consumables import estimate_consumable_life
from python_pkg.brother_printer.data_classes import (
    USBPortStatus,
    USBResult,
)

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)

# Directory holding the usblp device nodes, and the ioctl that reads the
# printer's IEEE 1284 status byte from one without disturbing the device.
USB_PRINTER_DEV_GLOB_DIR = "/dev/usb"
LPGETSTATUS = 0x060B


def _import_or_raise(name: str) -> types.ModuleType:
    """Import a module or raise ImportError with a helpful message."""
    try:
        return importlib.import_module(name)
    except ImportError as e:
        msg = f"{name} is required but not installed"
        raise ImportError(msg) from e


# ── pyusb device info ────────────────────────────────────────────────


def _get_pyusb_device_info() -> dict[str, str]:
    """Get Brother USB printer info via pyusb (no interface claim needed)."""
    try:
        usb_core = _import_or_raise("usb.core")

        dev = usb_core.find(idVendor=BROTHER_USB_VENDOR_ID)
        if dev is None:
            return {}
    except (ImportError, OSError, ValueError):
        return {}
    return {
        "product": dev.product or "",
        "serial": dev.serial_number or "",
    }


# ── CUPS service control ────────────────────────────────────────────


def is_cups_scheduler_running() -> bool:
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


def start_cups() -> bool:
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
    for _ in range(10):
        if is_cups_scheduler_running():
            return True
        time.sleep(1)
    return False


def _ensure_cups_running() -> bool:
    """Make sure CUPS is running, starting it if necessary."""
    if is_cups_scheduler_running():
        return True
    return start_cups()


# ── USB port status via pyusb ────────────────────────────────────────


def _port_status_from_byte(port_byte: int) -> USBPortStatus:
    """Decode a USB printer-class port status byte."""
    return USBPortStatus(
        paper_empty=bool(port_byte & 0x20),
        online=bool(port_byte & 0x10),
        # nFault is active low: the bit is set when there is NO fault.
        error=not bool(port_byte & 0x08),
        raw_byte=port_byte,
    )


def _port_status_via_usblp() -> USBPortStatus | None:
    """Read port status through the usblp device node. No side effects.

    The LPGETSTATUS ioctl returns the same byte as the USB control transfer
    but costs nothing: no stopping CUPS, no device reset, no driver detach.
    Returns None when the node is absent or busy.
    """
    dev_path = Path(USB_PRINTER_DEV_GLOB_DIR)
    devices = sorted(dev_path.glob("lp*")) if dev_path.is_dir() else []
    if not devices:
        return None
    try:
        # O_NONBLOCK: never hang here, the printer may be mid-job.
        fd = os.open(str(devices[0]), os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        logger.debug("opening %s failed", devices[0], exc_info=True)
        return None
    try:
        buf = bytearray(4)
        fcntl.ioctl(fd, LPGETSTATUS, buf)
    except OSError:
        logger.debug("usblp LPGETSTATUS failed", exc_info=True)
        return None
    finally:
        os.close(fd)
    return _port_status_from_byte(int.from_bytes(buf, "little") & 0xFF)


def _cups_is_busy(cups_state: str) -> bool:
    """Report whether CUPS is currently driving the printer."""
    return "processing" in cups_state.lower() or "printing" in cups_state.lower()


def _query_usb_port_status_raw(cups_state: str = "") -> USBPortStatus | None:
    """Query the printer's port status without disturbing it.

    Prefers the usblp ioctl, which is free. Falls back to a pyusb control
    transfer only when CUPS is idle: claiming the USB interface mid-job kills
    the print, and an earlier version of this function did exactly that - it
    stopped CUPS and reset the device just to read a status byte, destroying
    the job it was trying to report on.

    Args:
        cups_state: CUPS printer-state text, used to detect an active job.

    Returns:
        The port status, or None when it cannot be read harmlessly.
    """
    status = _port_status_via_usblp()
    if status is not None:
        return status

    if _cups_is_busy(cups_state):
        # A job is running and owns the device. Reading the status is not worth
        # killing the job for; the caller falls back to what CUPS reports.
        logger.debug("skipping USB probe: CUPS is printing")
        return None

    try:
        usb_core = _import_or_raise("usb.core")
        usb_util = _import_or_raise("usb.util")
    except ImportError:
        return None

    dev = usb_core.find(idVendor=BROTHER_USB_VENDOR_ID)
    if dev is None:
        return None

    detached = False
    try:
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
                detached = True
        except (usb_core.USBError, NotImplementedError):
            pass

        usb_util.claim_interface(dev, 0)
        try:
            # USB Printer Class GET_PORT_STATUS (bRequest=0x01)
            raw = dev.ctrl_transfer(0xA1, 0x01, 0, 0, 1, timeout=5000)
            return _port_status_from_byte(raw[0])
        finally:
            usb_util.release_interface(dev, 0)
            if detached:
                # Give usblp its device back, or /dev/usb/lp* stays missing and
                # every later run is stuck in this fallback path.
                with contextlib.suppress(Exception):
                    dev.attach_kernel_driver(0)
            usb_util.dispose_resources(dev)
    except (OSError, ValueError):
        logger.debug("USB port status query failed", exc_info=True)
        return None


# ── IPP / CUPS attribute queries ────────────────────────────────────


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
    command = [lpoptions_path, "-p", printer_name, "-l"]
    for line in run_command_text(command).splitlines():
        if "conomode" in line.lower():
            match = re.search(r"\*(\w+)", line)
            if match:
                return "ON" if match.group(1).lower() == "true" else "OFF"
    return ""


# ── Status code mapping ──────────────────────────────────────────────


def _map_cups_to_status_code(state: str, reasons: str) -> str:
    """Map CUPS state + reasons to a Brother PJL status code string."""
    for keyword, code in _CUPS_REASONS_TO_STATUS.items():
        if keyword in reasons.lower():
            return str(code)
    clean_state = re.sub(r"\(.*\)", "", state).strip().lower()
    return str(_CUPS_STATE_TO_STATUS.get(clean_state, 10001))


def _cups_reasons_to_error(cups_reasons: str) -> tuple[str, str]:
    """Map CUPS reason keywords to a (status_code, display) pair."""
    reasons_lower = cups_reasons.lower()
    for keywords, code, display in _ERROR_REASON_MAP:
        if any(kw in reasons_lower for kw in keywords):
            return code, display
    # Nothing recognised. Show what CUPS actually said rather than a bare
    # "Printer Error", which tells the reader nothing they can act on.
    detail = cups_reasons.strip()
    if detail and detail.lower() not in {"none", ""}:
        return DERIVED_CUPS_ERROR, f"Printer Error (CUPS reports: {detail})"
    return DERIVED_CUPS_ERROR, "Printer Error (CUPS gave no reason)"


def _port_status_to_status_code(
    ps: USBPortStatus,
    cups_reasons: str,
) -> tuple[str, str]:
    """Map USB port status + CUPS reasons to (status_code, display)."""
    # The port status exposes only paper_empty/error/online bits, so anything
    # more specific than "out of paper" has to come from the CUPS reasons -
    # an error bit alone does not tell us the cover is open.
    if ps.paper_empty:
        return "41000", "No Paper"
    if ps.error:
        return _cups_reasons_to_error(cups_reasons)
    if not ps.online:
        return "10002", "Offline / Sleep"
    return "", ""


# ── CUPS printer name discovery ──────────────────────────────────────


def find_cups_printer_name() -> str:
    """Find the CUPS queue name for a Brother printer."""
    lpstat_path = shutil.which("lpstat")
    if not lpstat_path:
        return ""
    for line in run_command_text([lpstat_path, "-v"]).splitlines():
        if "brother" in line.lower():
            match = re.match(r"device for (\S+):", line)
            if match:
                return match.group(1)
    return ""


# ── CUPS-based USB fallback query ────────────────────────────────────


def query_usb_via_cups() -> USBResult:
    """Query USB printer status through CUPS when /dev/usb/lp* is unavailable."""
    _ensure_cups_running()
    printer_name = find_cups_printer_name()
    if not printer_name:
        return USBResult(
            error="No USB printer device at /dev/usb/lp*"
            " (usblp module not available)"
            " and no Brother printer found in CUPS.",
        )

    pyusb_info = _get_pyusb_device_info()
    cups_info = printer_info_from_cups()

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

    port_status = _query_usb_port_status_raw(state)
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
        estimate = estimate_consumable_life()
        if estimate.toner_exhausted:
            result.status_code = DERIVED_TONER_END
            result.display = "Toner End (estimated from page count)"
            result.online = "TRUE"
            return result
        if estimate.toner_low:
            result.status_code = DERIVED_TONER_LOW
            result.display = "Toner Low (estimated from page count)"
            result.online = "TRUE"
            return result
        result.status_code = _map_cups_to_status_code(state, reasons)
        result.display = ipp.get("printer-state-message", "")
        result.online = "TRUE"
        return result

    result.status_code = _map_cups_to_status_code(state, reasons)
    result.display = ipp.get("printer-state-message", "")
    result.online = "TRUE" if state.lower() in {"idle", "processing"} else "FALSE"

    return result

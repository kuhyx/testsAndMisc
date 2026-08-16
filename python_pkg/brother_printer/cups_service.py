"""CUPS service management and raw USB port status.

The CUPS-based fallback query lives in _cups_fallback.py, and consumable life
tracking in consumables.py.
"""

from __future__ import annotations

import contextlib
import fcntl
import importlib
import logging
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import TYPE_CHECKING

from python_pkg.brother_printer.constants import BROTHER_USB_VENDOR_ID
from python_pkg.brother_printer.data_classes import USBPortStatus

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

"""CUPS service management, USB fallback, and consumable state tracking."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.parse

from python_pkg.brother_printer.constants import (
    _CUPS_REASONS_TO_STATUS,
    _CUPS_STATE_TO_STATUS,
    _ERROR_REASON_MAP,
    BROTHER_USB_VENDOR_ID,
    CONSUMABLE_STATE_DIR,
    CUPS_PAGE_LOG_PATH,
    DRUM_RATED_PAGES,
    GREEN,
    RESET,
    TONER_RATED_PAGES,
    _out,
)
from python_pkg.brother_printer.data_classes import (
    PageCountEstimate,
    USBPortStatus,
    USBResult,
)

logger = logging.getLogger(__name__)

CUPS_PAGE_LOG = Path(CUPS_PAGE_LOG_PATH)
CONSUMABLE_STATE_FILE = Path.home() / CONSUMABLE_STATE_DIR / "state.json"


# ── pyusb device info ────────────────────────────────────────────────


def _get_pyusb_device_info() -> dict[str, str]:
    """Get Brother USB printer info via pyusb (no interface claim needed)."""
    try:
        import usb.core

        dev = usb.core.find(idVendor=BROTHER_USB_VENDOR_ID)
        if dev is None:
            return {}
    except (ImportError, OSError, ValueError):
        return {}
    else:
        return {
            "product": dev.product or "",
            "serial": dev.serial_number or "",
        }


# ── CUPS service control ────────────────────────────────────────────


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
    except (OSError, ValueError):
        logger.debug("USB port status query failed", exc_info=True)
        return None
    finally:
        start_cups()


# ── Consumable state management ──────────────────────────────────────


def _get_cups_total_pages() -> int:
    """Parse CUPS page_log to get total pages printed (deduplicated by job)."""
    if not CUPS_PAGE_LOG.exists():
        return 0
    try:
        text = CUPS_PAGE_LOG.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    jobs: dict[str, int] = {}
    for line in text.splitlines():
        match = re.search(r"\s(\d+)\s+\[.*?\]\s+total\s+(\d+)", line)
        if match:
            job_id = match.group(1)
            pages = int(match.group(2))
            jobs[job_id] = max(jobs.get(job_id, 0), pages)
    return sum(jobs.values())


def _load_consumable_state() -> dict[str, int]:
    """Load consumable replacement state from disk."""
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


def reset_consumable(name: str) -> None:
    """Record current page count as replacement point for a consumable."""
    total = _get_cups_total_pages()
    state = _load_consumable_state()
    key = f"{name}_replaced_at"
    state[key] = total
    _save_consumable_state(state)
    _out(f"{GREEN}✓ {name.capitalize()} counter reset at page count {total}.{RESET}")
    _out(f"  State saved to {CONSUMABLE_STATE_FILE}")


def estimate_consumable_life() -> PageCountEstimate:
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
    return "42000", "Printer Error"


def _port_status_to_status_code(
    ps: USBPortStatus,
    cups_reasons: str,
) -> tuple[str, str]:
    """Map USB port status + CUPS reasons to (status_code, display)."""
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


# ── CUPS printer name discovery ──────────────────────────────────────


def find_cups_printer_name() -> str:
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
                match = re.match(r"device for (\S+):", line)
                if match:
                    return match.group(1)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass
    return ""


# ── CUPS-based USB fallback query ────────────────────────────────────


def _parse_cups_usb_uri(uri: str, info: dict[str, str]) -> None:
    """Extract product and serial from a CUPS usb:// URI."""
    parsed = urllib.parse.urlparse(uri)
    info["product"] = urllib.parse.unquote(parsed.path.lstrip("/"))
    qs = urllib.parse.parse_qs(parsed.query)
    if "serial" in qs:
        info["serial"] = qs["serial"][0]


def _get_printer_info_from_cups() -> dict[str, str]:
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
    cups_info = _get_printer_info_from_cups()

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
        estimate = estimate_consumable_life()
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

    result.status_code = _map_cups_to_status_code(state, reasons)
    result.display = ipp.get("printer-state-message", "")
    result.online = "TRUE" if state.lower() in {"idle", "processing"} else "FALSE"

    return result

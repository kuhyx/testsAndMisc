"""IPP attribute queries, CUPS status mapping, and the CUPS-based USB fallback.

Split out of :mod:`python_pkg.brother_printer.cups_service` to keep it under
the 250-line cap. The service-control and raw USB port-status helpers stay in
``cups_service``, which patches ``fcntl``, ``os``, ``Path`` and ``time`` on
that module; they are imported here so ``tests/test_cups_service_part3.py``
can patch them on this one.
"""

from __future__ import annotations

import re
import shutil
import subprocess

from python_pkg.brother_printer._query import (
    printer_info_from_cups,
    run_command_text,
)
from python_pkg.brother_printer.constants import (
    _CUPS_REASONS_TO_STATUS,
    _CUPS_STATE_TO_STATUS,
    _ERROR_REASON_MAP,
    DERIVED_CUPS_ERROR,
    DERIVED_TONER_END,
    DERIVED_TONER_LOW,
)
from python_pkg.brother_printer.consumables import estimate_consumable_life
from python_pkg.brother_printer.cups_service import (
    _ensure_cups_running,
    _get_pyusb_device_info,
    _query_usb_port_status_raw,
)
from python_pkg.brother_printer.data_classes import (
    USBPortStatus,
    USBResult,
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
    except subprocess.TimeoutExpired, subprocess.SubprocessError, OSError:
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

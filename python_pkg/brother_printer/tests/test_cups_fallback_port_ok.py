"""Tests for brother_printer._cups_fallback - fallback with a healthy port.

Split from test_cups_service_part3.py under the 250-line cap. When the USB port
reports no hardware fault, the status has to be derived from the page-count
estimate or from the CUPS state, which is what these cover.
"""

from __future__ import annotations

from unittest.mock import patch

from python_pkg.brother_printer._cups_fallback import query_usb_via_cups
from python_pkg.brother_printer.constants import (
    DERIVED_TONER_END,
    DERIVED_TONER_LOW,
)
from python_pkg.brother_printer.data_classes import (
    PageCountEstimate,
    USBPortStatus,
)

MOD = "python_pkg.brother_printer._cups_fallback"


class TestQueryUsbViaCupsPortOk:
    """query_usb_via_cups when the USB port status reports no fault."""

    def test_port_ok_toner_exhausted(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}.printer_info_from_cups",
                return_value={"product": "", "serial": ""},
            ),
            patch(
                f"{MOD}._get_cups_ipp_status",
                return_value={
                    "printer-state": "idle",
                    "printer-state-reasons": "none",
                },
            ),
            patch(f"{MOD}._get_cups_economode", return_value=""),
            patch(
                f"{MOD}._query_usb_port_status_raw",
                return_value=USBPortStatus(
                    error=False,
                    paper_empty=False,
                    online=True,
                    raw_byte=0x18,
                ),
            ),
            patch(
                f"{MOD}.estimate_consumable_life",
                return_value=PageCountEstimate(
                    toner_exhausted=True,
                    total_pages=1000,
                    toner_pages=1000,
                ),
            ),
        ):
            result = query_usb_via_cups()
            assert result.status_code == DERIVED_TONER_END
            assert "Toner End" in result.display

    def test_port_ok_toner_low(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}.printer_info_from_cups",
                return_value={"product": "", "serial": ""},
            ),
            patch(
                f"{MOD}._get_cups_ipp_status",
                return_value={
                    "printer-state": "idle",
                    "printer-state-reasons": "none",
                },
            ),
            patch(f"{MOD}._get_cups_economode", return_value=""),
            patch(
                f"{MOD}._query_usb_port_status_raw",
                return_value=USBPortStatus(
                    error=False,
                    paper_empty=False,
                    online=True,
                    raw_byte=0x18,
                ),
            ),
            patch(
                f"{MOD}.estimate_consumable_life",
                return_value=PageCountEstimate(
                    toner_low=True,
                    total_pages=800,
                    toner_pages=800,
                ),
            ),
        ):
            result = query_usb_via_cups()
            assert result.status_code == DERIVED_TONER_LOW
            assert "Toner Low" in result.display

    def test_port_ok_normal(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}.printer_info_from_cups",
                return_value={"product": "", "serial": ""},
            ),
            patch(
                f"{MOD}._get_cups_ipp_status",
                return_value={
                    "printer-state": "idle",
                    "printer-state-reasons": "none",
                    "printer-state-message": "Ready",
                },
            ),
            patch(f"{MOD}._get_cups_economode", return_value=""),
            patch(
                f"{MOD}._query_usb_port_status_raw",
                return_value=USBPortStatus(
                    error=False,
                    paper_empty=False,
                    online=True,
                    raw_byte=0x18,
                ),
            ),
            patch(
                f"{MOD}.estimate_consumable_life",
                return_value=PageCountEstimate(total_pages=100, toner_pages=100),
            ),
        ):
            result = query_usb_via_cups()
            assert result.online == "TRUE"
            assert result.display == "Ready"

    def test_port_error_uses_cups_reasons(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(
                f"{MOD}._get_pyusb_device_info",
                return_value={"product": "HL-1110", "serial": "SN1"},
            ),
            patch(
                f"{MOD}.printer_info_from_cups",
                return_value={"product": "", "serial": ""},
            ),
            patch(
                f"{MOD}._get_cups_ipp_status",
                return_value={
                    "printer-state": "stopped",
                    "printer-state-reasons": "media-jam",
                },
            ),
            patch(f"{MOD}._get_cups_economode", return_value=""),
            patch(
                f"{MOD}._query_usb_port_status_raw",
                return_value=USBPortStatus(
                    error=True,
                    paper_empty=False,
                    online=True,
                    raw_byte=0x00,
                ),
            ),
        ):
            result = query_usb_via_cups()
            assert result.status_code == "40022"
            assert result.product == "HL-1110"
            assert result.online == "TRUE"

"""Tests for brother_printer.cups_service module - part 3 (query_usb_via_cups)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    query_usb_via_cups,
)
from python_pkg.brother_printer.data_classes import (
    PageCountEstimate,
    USBPortStatus,
)

MOD = "python_pkg.brother_printer.cups_service"


# ── query_usb_via_cups ───────────────────────────────────────────────


class TestQueryUsbViaCups:
    """Tests for query_usb_via_cups."""

    @patch(f"{MOD}.find_cups_printer_name", return_value="")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_no_printer(self, e: MagicMock, f: MagicMock) -> None:
        result = query_usb_via_cups()
        assert result.error != ""

    def test_no_port_status_idle(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}._get_printer_info_from_cups",
                return_value={"product": "HL-1110", "serial": "ABC"},
            ),
            patch(
                f"{MOD}._get_cups_ipp_status",
                return_value={
                    "printer-state": "idle",
                    "printer-state-reasons": "none",
                    "printer-state-message": "Ready",
                },
            ),
            patch(f"{MOD}._get_cups_economode", return_value="ON"),
            patch(f"{MOD}._query_usb_port_status_raw", return_value=None),
        ):
            result = query_usb_via_cups()
            assert result.online == "TRUE"
            assert result.product == "HL-1110"
            assert result.economode == "ON"

    def test_no_port_status_stopped(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}._get_printer_info_from_cups",
                return_value={"product": "", "serial": ""},
            ),
            patch(
                f"{MOD}._get_cups_ipp_status",
                return_value={
                    "printer-state": "stopped",
                    "printer-state-reasons": "none",
                },
            ),
            patch(f"{MOD}._get_cups_economode", return_value=""),
            patch(f"{MOD}._query_usb_port_status_raw", return_value=None),
        ):
            result = query_usb_via_cups()
            assert result.online == "FALSE"
            assert result.product == "Brother Laser Printer"

    def test_port_status_hw_error(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}._get_printer_info_from_cups",
                return_value={"product": "", "serial": ""},
            ),
            patch(
                f"{MOD}._get_cups_ipp_status",
                return_value={
                    "printer-state": "stopped",
                    "printer-state-reasons": "none",
                },
            ),
            patch(f"{MOD}._get_cups_economode", return_value=""),
            patch(
                f"{MOD}._query_usb_port_status_raw",
                return_value=USBPortStatus(
                    error=True,
                    paper_empty=True,
                    online=False,
                    raw_byte=0x20,
                ),
            ),
        ):
            result = query_usb_via_cups()
            assert result.status_code == "40302"
            assert result.online == "FALSE"

    def test_port_ok_toner_exhausted(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}._get_printer_info_from_cups",
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
            assert result.status_code == "40310"
            assert "Toner End" in result.display

    def test_port_ok_toner_low(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}._get_printer_info_from_cups",
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
            assert result.status_code == "30010"
            assert "Toner Low" in result.display

    def test_port_ok_normal(self) -> None:
        with (
            patch(f"{MOD}._ensure_cups_running", return_value=True),
            patch(f"{MOD}.find_cups_printer_name", return_value="Brother"),
            patch(f"{MOD}._get_pyusb_device_info", return_value={}),
            patch(
                f"{MOD}._get_printer_info_from_cups",
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
                f"{MOD}._get_printer_info_from_cups",
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
            assert result.status_code == "40000"
            assert result.product == "HL-1110"
            assert result.online == "TRUE"

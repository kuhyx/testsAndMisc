"""Tests for brother_printer._cups_fallback - the CUPS fallback query."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer._cups_fallback import query_usb_via_cups
from python_pkg.brother_printer.data_classes import USBPortStatus

MOD = "python_pkg.brother_printer._cups_fallback"


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
                f"{MOD}.printer_info_from_cups",
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
                f"{MOD}.printer_info_from_cups",
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
                f"{MOD}.printer_info_from_cups",
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
            assert result.status_code == "41000"
            assert result.online == "FALSE"

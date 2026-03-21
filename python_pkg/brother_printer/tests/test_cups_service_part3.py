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
    def test_no_printer(self, _e: MagicMock, _f: MagicMock) -> None:
        result = query_usb_via_cups()
        assert result.error != ""

    @patch(f"{MOD}._query_usb_port_status_raw", return_value=None)
    @patch(f"{MOD}._get_cups_economode", return_value="ON")
    @patch(
        f"{MOD}._get_cups_ipp_status",
        return_value={
            "printer-state": "idle",
            "printer-state-reasons": "none",
            "printer-state-message": "Ready",
        },
    )
    @patch(
        f"{MOD}._get_printer_info_from_cups",
        return_value={"product": "HL-1110", "serial": "ABC"},
    )
    @patch(f"{MOD}._get_pyusb_device_info", return_value={})
    @patch(f"{MOD}.find_cups_printer_name", return_value="Brother")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_no_port_status_idle(
        self,
        _e: MagicMock,
        _f: MagicMock,
        _py: MagicMock,
        _cups: MagicMock,
        _ipp: MagicMock,
        _eco: MagicMock,
        _port: MagicMock,
    ) -> None:
        result = query_usb_via_cups()
        assert result.online == "TRUE"
        assert result.product == "HL-1110"
        assert result.economode == "ON"

    @patch(f"{MOD}._query_usb_port_status_raw", return_value=None)
    @patch(f"{MOD}._get_cups_economode", return_value="")
    @patch(
        f"{MOD}._get_cups_ipp_status",
        return_value={
            "printer-state": "stopped",
            "printer-state-reasons": "none",
        },
    )
    @patch(
        f"{MOD}._get_printer_info_from_cups",
        return_value={"product": "", "serial": ""},
    )
    @patch(f"{MOD}._get_pyusb_device_info", return_value={})
    @patch(f"{MOD}.find_cups_printer_name", return_value="Brother")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_no_port_status_stopped(
        self,
        _e: MagicMock,
        _f: MagicMock,
        _py: MagicMock,
        _cups: MagicMock,
        _ipp: MagicMock,
        _eco: MagicMock,
        _port: MagicMock,
    ) -> None:
        result = query_usb_via_cups()
        assert result.online == "FALSE"
        assert result.product == "Brother Laser Printer"

    @patch(
        f"{MOD}._query_usb_port_status_raw",
        return_value=USBPortStatus(
            error=True,
            paper_empty=True,
            online=False,
            raw_byte=0x20,
        ),
    )
    @patch(f"{MOD}._get_cups_economode", return_value="")
    @patch(
        f"{MOD}._get_cups_ipp_status",
        return_value={
            "printer-state": "stopped",
            "printer-state-reasons": "none",
        },
    )
    @patch(
        f"{MOD}._get_printer_info_from_cups",
        return_value={"product": "", "serial": ""},
    )
    @patch(f"{MOD}._get_pyusb_device_info", return_value={})
    @patch(f"{MOD}.find_cups_printer_name", return_value="Brother")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_port_status_hw_error(
        self,
        _e: MagicMock,
        _f: MagicMock,
        _py: MagicMock,
        _cups: MagicMock,
        _ipp: MagicMock,
        _eco: MagicMock,
        _port: MagicMock,
    ) -> None:
        result = query_usb_via_cups()
        assert result.status_code == "40302"
        assert result.online == "FALSE"

    @patch(
        f"{MOD}.estimate_consumable_life",
        return_value=PageCountEstimate(
            toner_exhausted=True,
            total_pages=1000,
            toner_pages=1000,
        ),
    )
    @patch(
        f"{MOD}._query_usb_port_status_raw",
        return_value=USBPortStatus(
            error=False,
            paper_empty=False,
            online=True,
            raw_byte=0x18,
        ),
    )
    @patch(f"{MOD}._get_cups_economode", return_value="")
    @patch(
        f"{MOD}._get_cups_ipp_status",
        return_value={
            "printer-state": "idle",
            "printer-state-reasons": "none",
        },
    )
    @patch(
        f"{MOD}._get_printer_info_from_cups",
        return_value={"product": "", "serial": ""},
    )
    @patch(f"{MOD}._get_pyusb_device_info", return_value={})
    @patch(f"{MOD}.find_cups_printer_name", return_value="Brother")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_port_ok_toner_exhausted(
        self,
        _e: MagicMock,
        _f: MagicMock,
        _py: MagicMock,
        _cups: MagicMock,
        _ipp: MagicMock,
        _eco: MagicMock,
        _port: MagicMock,
        _est: MagicMock,
    ) -> None:
        result = query_usb_via_cups()
        assert result.status_code == "40310"
        assert "Toner End" in result.display

    @patch(
        f"{MOD}.estimate_consumable_life",
        return_value=PageCountEstimate(
            toner_low=True,
            total_pages=800,
            toner_pages=800,
        ),
    )
    @patch(
        f"{MOD}._query_usb_port_status_raw",
        return_value=USBPortStatus(
            error=False,
            paper_empty=False,
            online=True,
            raw_byte=0x18,
        ),
    )
    @patch(f"{MOD}._get_cups_economode", return_value="")
    @patch(
        f"{MOD}._get_cups_ipp_status",
        return_value={
            "printer-state": "idle",
            "printer-state-reasons": "none",
        },
    )
    @patch(
        f"{MOD}._get_printer_info_from_cups",
        return_value={"product": "", "serial": ""},
    )
    @patch(f"{MOD}._get_pyusb_device_info", return_value={})
    @patch(f"{MOD}.find_cups_printer_name", return_value="Brother")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_port_ok_toner_low(
        self,
        _e: MagicMock,
        _f: MagicMock,
        _py: MagicMock,
        _cups: MagicMock,
        _ipp: MagicMock,
        _eco: MagicMock,
        _port: MagicMock,
        _est: MagicMock,
    ) -> None:
        result = query_usb_via_cups()
        assert result.status_code == "30010"
        assert "Toner Low" in result.display

    @patch(
        f"{MOD}.estimate_consumable_life",
        return_value=PageCountEstimate(total_pages=100, toner_pages=100),
    )
    @patch(
        f"{MOD}._query_usb_port_status_raw",
        return_value=USBPortStatus(
            error=False,
            paper_empty=False,
            online=True,
            raw_byte=0x18,
        ),
    )
    @patch(f"{MOD}._get_cups_economode", return_value="")
    @patch(
        f"{MOD}._get_cups_ipp_status",
        return_value={
            "printer-state": "idle",
            "printer-state-reasons": "none",
            "printer-state-message": "Ready",
        },
    )
    @patch(
        f"{MOD}._get_printer_info_from_cups",
        return_value={"product": "", "serial": ""},
    )
    @patch(f"{MOD}._get_pyusb_device_info", return_value={})
    @patch(f"{MOD}.find_cups_printer_name", return_value="Brother")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_port_ok_normal(
        self,
        _e: MagicMock,
        _f: MagicMock,
        _py: MagicMock,
        _cups: MagicMock,
        _ipp: MagicMock,
        _eco: MagicMock,
        _port: MagicMock,
        _est: MagicMock,
    ) -> None:
        result = query_usb_via_cups()
        assert result.online == "TRUE"
        assert result.display == "Ready"

    @patch(
        f"{MOD}._query_usb_port_status_raw",
        return_value=USBPortStatus(
            error=True,
            paper_empty=False,
            online=True,
            raw_byte=0x00,
        ),
    )
    @patch(f"{MOD}._get_cups_economode", return_value="")
    @patch(
        f"{MOD}._get_cups_ipp_status",
        return_value={
            "printer-state": "stopped",
            "printer-state-reasons": "media-jam",
        },
    )
    @patch(
        f"{MOD}._get_printer_info_from_cups",
        return_value={"product": "", "serial": ""},
    )
    @patch(
        f"{MOD}._get_pyusb_device_info",
        return_value={"product": "HL-1110", "serial": "SN1"},
    )
    @patch(f"{MOD}.find_cups_printer_name", return_value="Brother")
    @patch(f"{MOD}._ensure_cups_running", return_value=True)
    def test_port_error_uses_cups_reasons(
        self,
        _e: MagicMock,
        _f: MagicMock,
        _py: MagicMock,
        _cups: MagicMock,
        _ipp: MagicMock,
        _eco: MagicMock,
        _port: MagicMock,
    ) -> None:
        result = query_usb_via_cups()
        assert result.status_code == "40000"
        assert result.product == "HL-1110"
        assert result.online == "TRUE"

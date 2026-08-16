"""Tests for brother_printer.display module."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brother_printer.data_classes import (
    USBPortStatus,
    USBResult,
)
from python_pkg.brother_printer.display import (
    _display_cups_fallback_note,
    _display_pjl_status,
    _display_report_header,
    _display_usb_device_info,
    _format_status_detail,
    display_usb_results,
)

MOD = "python_pkg.brother_printer.display"


class TestDisplayReportHeader:
    def test_prints_header(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_report_header()
            assert "Brother Laser Printer" in out.getvalue()


class TestDisplayUsbDeviceInfo:
    def test_full_info(self) -> None:
        r = USBResult(
            product="HL-1110",
            serial="SN123",
            online="TRUE",
            economode="ON",
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_usb_device_info(r)
            text = out.getvalue()
            assert "HL-1110" in text
            assert "SN123" in text
            assert "Yes" in text
            assert "Toner Save" in text

    def test_offline(self) -> None:
        r = USBResult(online="FALSE")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_usb_device_info(r)
            assert "No (needs attention)" in out.getvalue()

    def test_no_online(self) -> None:
        r = USBResult(online="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_usb_device_info(r)
            assert "Online" not in out.getvalue()

    def test_economode_off(self) -> None:
        r = USBResult(economode="OFF")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_usb_device_info(r)
            assert "OFF" in out.getvalue()

    def test_no_economode(self) -> None:
        r = USBResult(economode="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_usb_device_info(r)
            assert "Toner Save" not in out.getvalue()

    def test_no_serial(self) -> None:
        r = USBResult(serial="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_usb_device_info(r)
            assert "Serial" not in out.getvalue()

    def test_no_product(self) -> None:
        r = USBResult(product="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_usb_device_info(r)
            assert "Unknown" in out.getvalue()


class TestFormatStatusDetail:
    def test_with_action(self) -> None:
        r = USBResult(
            status_code="30010",
            display="Toner Low Display",
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _format_status_detail("warn", "Toner Low", "Replace toner", r)
            text = out.getvalue()
            assert "Toner Low" in text
            assert "Replace toner" in text
            assert "Display:" in text

    def test_no_action(self) -> None:
        r = USBResult(status_code="10001", display="Ready")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _format_status_detail("ok", "Ready", "", r)
            assert "Action" not in out.getvalue()

    def test_display_same_as_text(self) -> None:
        r = USBResult(status_code="10001", display="Ready")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _format_status_detail("ok", "Ready", "", r)
            assert "Display:" not in out.getvalue()

    def test_unknown_severity(self) -> None:
        r = USBResult(status_code="99999", display="")
        with patch("sys.stdout", new_callable=StringIO):
            _format_status_detail("unknown", "Test", "", r)
            # Should not crash

    def test_critical(self) -> None:
        r = USBResult(status_code="40310", display="Toner End")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _format_status_detail("critical", "Toner End", "Replace", r)
            assert "ACTION REQUIRED" in out.getvalue()

    def test_info(self) -> None:
        r = USBResult(status_code="10006", display="Processing")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _format_status_detail("info", "Processing", "", r)
            assert "busy" in out.getvalue()


class TestDisplayPjlStatus:
    def test_no_code(self) -> None:
        r = USBResult(status_code="", display="hello")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_pjl_status(r)
            assert "Could not read status" in out.getvalue()
            assert "hello" in out.getvalue()

    def test_no_code_no_display(self) -> None:
        r = USBResult(status_code="", display="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_pjl_status(r)
            assert "Could not read status" in out.getvalue()

    @patch(f"{MOD}._format_status_detail")
    @patch(f"{MOD}.get_status_info", return_value=("ok", "Ready", ""))
    def test_with_code(self, g: MagicMock, mock_fmt: MagicMock) -> None:
        r = USBResult(status_code="10001")
        with patch("sys.stdout", new_callable=StringIO):
            _display_pjl_status(r)
        mock_fmt.assert_called_once()


class TestDisplayCupsFallbackNote:
    def test_with_port_status(self) -> None:
        r = USBResult(port_status=USBPortStatus())
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_cups_fallback_note(r)
            assert "USB port query" in out.getvalue()

    def test_without_port_status(self) -> None:
        r = USBResult(port_status=None)
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_cups_fallback_note(r)
            assert "pyusb not available" in out.getvalue()


class TestDisplayUsbResults:
    def test_normal(self) -> None:
        r = USBResult(device="/dev/usb/lp0")
        with (
            patch(f"{MOD}._display_report_header"),
            patch(f"{MOD}._display_usb_device_info"),
            patch(f"{MOD}._display_pjl_status"),
            patch(f"{MOD}._display_page_count_estimate"),
            patch(f"{MOD}._display_consumables_reference"),
            patch(f"{MOD}.get_cups_queue_status"),
            patch(f"{MOD}.display_cups_queue_status"),
            patch("sys.stdout", new_callable=StringIO),
        ):
            display_usb_results(r)

    def test_cups_device(self) -> None:
        r = USBResult(device="cups")
        with (
            patch(f"{MOD}._display_report_header"),
            patch(f"{MOD}._display_usb_device_info"),
            patch(f"{MOD}._display_pjl_status"),
            patch(f"{MOD}._display_page_count_estimate"),
            patch(f"{MOD}._display_consumables_reference"),
            patch(f"{MOD}.get_cups_queue_status"),
            patch(f"{MOD}.display_cups_queue_status"),
            patch(f"{MOD}._display_cups_fallback_note") as mock_fallback,
            patch("sys.stdout", new_callable=StringIO),
        ):
            display_usb_results(r)
            mock_fallback.assert_called_once()

    def test_error(self) -> None:
        r = USBResult(error="fail")
        with (
            patch("sys.stdout", new_callable=StringIO),
            pytest.raises(SystemExit),
        ):
            display_usb_results(r)

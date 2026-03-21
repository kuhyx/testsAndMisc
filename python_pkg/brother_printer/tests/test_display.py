"""Tests for brother_printer.display module."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brother_printer.data_classes import (
    NetworkResult,
    PageCountEstimate,
    USBPortStatus,
    USBResult,
)
from python_pkg.brother_printer.display import (
    _classify_percentage_level,
    _classify_supply_level,
    _collect_supply_items,
    _display_consumables_reference,
    _display_cups_fallback_note,
    _display_page_count_estimate,
    _display_pjl_status,
    _display_report_header,
    _display_supply_levels,
    _display_supply_warnings,
    _display_usb_device_info,
    _format_status_detail,
    _format_supply_bar,
    _parse_supply_value,
    _process_supply_item,
    display_usb_results,
)

MOD = "python_pkg.brother_printer.display"


class TestDisplayReportHeader:
    def test_prints_header(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_report_header()
            assert "Brother Laser Printer" in out.getvalue()


class TestDisplayPageCountEstimate:
    @patch(f"{MOD}.estimate_consumable_life")
    def test_no_pages(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(total_pages=0)
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert out.getvalue() == ""

    @patch(f"{MOD}.estimate_consumable_life")
    def test_healthy(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=100,
            toner_pages=100,
            drum_pages=100,
            toner_pct_remaining=90,
            drum_pct_remaining=99,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "Total pages" in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_toner_exhausted(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=1000,
            toner_pages=1000,
            drum_pages=100,
            toner_pct_remaining=0,
            drum_pct_remaining=99,
            toner_exhausted=True,
            toner_low=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "REPLACE NOW" in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_toner_low(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=800,
            toner_pages=800,
            drum_pages=100,
            toner_pct_remaining=20,
            drum_pct_remaining=99,
            toner_low=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "order soon" in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_drum_near_end(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=9000,
            toner_pages=100,
            drum_pages=9000,
            toner_pct_remaining=90,
            drum_pct_remaining=10,
            drum_near_end=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "nearing end" in out.getvalue()


class TestDisplayConsumablesReference:
    def test_prints(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_consumables_reference()
            assert "TN-1050" in out.getvalue()


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
    def test_with_code(self, _g: MagicMock, mock_fmt: MagicMock) -> None:
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
    @patch(f"{MOD}.display_cups_queue_status")
    @patch(f"{MOD}.get_cups_queue_status")
    @patch(f"{MOD}._display_consumables_reference")
    @patch(f"{MOD}._display_page_count_estimate")
    @patch(f"{MOD}._display_pjl_status")
    @patch(f"{MOD}._display_usb_device_info")
    @patch(f"{MOD}._display_report_header")
    def test_normal(
        self,
        _h: MagicMock,
        _d: MagicMock,
        _p: MagicMock,
        _pe: MagicMock,
        _c: MagicMock,
        _gq: MagicMock,
        _dq: MagicMock,
    ) -> None:
        r = USBResult(device="/dev/usb/lp0")
        with patch("sys.stdout", new_callable=StringIO):
            display_usb_results(r)

    @patch(f"{MOD}._display_cups_fallback_note")
    @patch(f"{MOD}.display_cups_queue_status")
    @patch(f"{MOD}.get_cups_queue_status")
    @patch(f"{MOD}._display_consumables_reference")
    @patch(f"{MOD}._display_page_count_estimate")
    @patch(f"{MOD}._display_pjl_status")
    @patch(f"{MOD}._display_usb_device_info")
    @patch(f"{MOD}._display_report_header")
    def test_cups_device(
        self,
        _h: MagicMock,
        _d: MagicMock,
        _p: MagicMock,
        _pe: MagicMock,
        _c: MagicMock,
        _gq: MagicMock,
        _dq: MagicMock,
        mock_fallback: MagicMock,
    ) -> None:
        r = USBResult(device="cups")
        with patch("sys.stdout", new_callable=StringIO):
            display_usb_results(r)
        mock_fallback.assert_called_once()

    def test_error(self) -> None:
        r = USBResult(error="fail")
        with (
            patch("sys.stdout", new_callable=StringIO),
            pytest.raises(SystemExit),
        ):
            display_usb_results(r)


class TestClassifyPercentageLevel:
    def test_low(self) -> None:
        pct, text, color, warn, replace = _classify_percentage_level("Toner", 5)
        assert pct == 5
        assert replace is True

    def test_warn(self) -> None:
        pct, text, color, warn, replace = _classify_percentage_level("Toner", 20)
        assert replace is False
        assert "order soon" in warn

    def test_ok(self) -> None:
        pct, text, color, warn, replace = _classify_percentage_level("Toner", 80)
        assert replace is False
        assert warn == ""


class TestClassifySupplyLevel:
    def test_snmp_ok(self) -> None:
        pct, text, color, warn, replace = _classify_supply_level("Toner", 100, -3)
        assert text == "OK"
        assert replace is False

    def test_snmp_low(self) -> None:
        pct, text, color, warn, replace = _classify_supply_level("Toner", 100, -2)
        assert text == "LOW"
        assert replace is True

    def test_empty(self) -> None:
        pct, text, color, warn, replace = _classify_supply_level("Toner", 100, 0)
        assert text == "EMPTY"
        assert replace is True

    def test_normal_percentage(self) -> None:
        pct, text, color, warn, replace = _classify_supply_level("Toner", 100, 80)
        assert pct == 80
        assert replace is False

    def test_no_max_val(self) -> None:
        pct, text, color, warn, replace = _classify_supply_level("Toner", 0, 50)
        assert pct == -1
        assert text == ""

    def test_over_100_capped(self) -> None:
        pct, text, color, warn, replace = _classify_supply_level("Toner", 50, 100)
        assert pct == 100


class TestFormatSupplyBar:
    def test_negative(self) -> None:
        assert _format_supply_bar(-1) == ""

    def test_zero(self) -> None:
        bar = _format_supply_bar(0)
        assert "░" in bar

    def test_full(self) -> None:
        bar = _format_supply_bar(100)
        assert "█" in bar


class TestProcessSupplyItem:
    def test_normal(self) -> None:
        item = _process_supply_item("Toner", 100, 80)
        assert item.status_text == "80%"

    def test_empty(self) -> None:
        item = _process_supply_item("Toner", 100, 0)
        assert item.needs_replacement is True


class TestDisplaySupplyWarnings:
    def test_replacement_needed(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_warnings(
                needs_replacement=True,
                warnings=["Toner low"],
            )
            assert "ACTION NEEDED" in out.getvalue()

    def test_warnings_only(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_warnings(
                needs_replacement=False,
                warnings=["Toner at 20%"],
            )
            assert "HEADS UP" in out.getvalue()

    def test_all_healthy(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_warnings(
                needs_replacement=False,
                warnings=[],
            )
            assert "healthy" in out.getvalue()


class TestParseSupplyValue:
    def test_valid(self) -> None:
        assert _parse_supply_value(["10", "20"], 0) == 10

    def test_index_error(self) -> None:
        assert _parse_supply_value([], 0) == 0

    def test_value_error(self) -> None:
        assert _parse_supply_value(["abc"], 0) == 0


class TestCollectSupplyItems:
    def test_collect(self) -> None:
        result = NetworkResult(
            supply_descriptions=["Toner", "Drum"],
            supply_max=["100", "200"],
            supply_levels=["80", "150"],
        )
        items, descs = _collect_supply_items(result)
        assert len(items) == 2
        assert descs == ["Toner", "Drum"]


class TestDisplaySupplyLevels:
    def test_with_items(self) -> None:
        result = NetworkResult(
            supply_descriptions=["Toner"],
            supply_max=["100"],
            supply_levels=["80"],
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_levels(result)
            assert "Toner" in out.getvalue()

    def test_needs_replacement_and_warning(self) -> None:
        result = NetworkResult(
            supply_descriptions=["Toner", "Drum"],
            supply_max=["100", "100"],
            supply_levels=["0", "15"],
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_levels(result)
            text = out.getvalue()
            assert "ACTION NEEDED" in text

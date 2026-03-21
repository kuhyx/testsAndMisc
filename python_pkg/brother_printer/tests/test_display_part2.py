"""Tests for brother_printer.display module - part 2 (network display)."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brother_printer.data_classes import (
    NetworkResult,
)
from python_pkg.brother_printer.display import (
    _display_network_device_info,
    display_network_results,
)

MOD = "python_pkg.brother_printer.display"


class TestDisplayNetworkDeviceInfo:
    def test_full_info(self) -> None:
        result = NetworkResult(
            ip="1.2.3.4",
            product="HL-1110",
            serial="SN1",
            display="Ready",
            page_count="500",
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_network_device_info(result)
            text = out.getvalue()
            assert "HL-1110" in text
            assert "1.2.3.4" in text
            assert "SN1" in text
            assert "500" in text

    def test_no_serial(self) -> None:
        result = NetworkResult(ip="1.2.3.4")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_network_device_info(result)
            assert "Serial" not in out.getvalue()

    def test_no_display(self) -> None:
        result = NetworkResult(ip="1.2.3.4")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_network_device_info(result)
            assert "Display" not in out.getvalue()

    def test_non_digit_page_count(self) -> None:
        result = NetworkResult(ip="1.2.3.4", page_count="abc")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_network_device_info(result)
            assert "Pages" not in out.getvalue()

    def test_no_page_count(self) -> None:
        result = NetworkResult(ip="1.2.3.4", page_count="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_network_device_info(result)
            assert "Pages" not in out.getvalue()

    def test_no_product(self) -> None:
        result = NetworkResult(ip="1.2.3.4", product="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_network_device_info(result)
            assert "Unknown" in out.getvalue()


class TestDisplayNetworkResults:
    @patch(f"{MOD}._display_supply_levels")
    @patch(f"{MOD}._display_network_device_info")
    @patch(f"{MOD}._display_report_header")
    def test_normal(
        self,
        _h: MagicMock,
        _d: MagicMock,
        _s: MagicMock,
    ) -> None:
        r = NetworkResult(ip="1.2.3.4")
        with patch("sys.stdout", new_callable=StringIO) as out:
            display_network_results(r)
            assert "1.2.3.4" in out.getvalue()

    def test_error(self) -> None:
        r = NetworkResult(error="fail")
        with (
            patch("sys.stdout", new_callable=StringIO),
            pytest.raises(SystemExit),
        ):
            display_network_results(r)

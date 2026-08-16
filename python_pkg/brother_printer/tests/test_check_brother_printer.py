"""Tests for brother_printer.check_brother_printer - discovery and modes."""

from __future__ import annotations

from io import StringIO
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brother_printer.check_brother_printer import (
    _discover_network_printer,
    _no_printer_found,
    _run_network_mode,
    _run_usb_mode,
)
from python_pkg.brother_printer.data_classes import USBResult

MOD = "python_pkg.brother_printer.check_brother_printer"


class TestDiscoverNetworkPrinter:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, m: MagicMock) -> None:
        assert _discover_network_printer() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_found_ip(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: ipp://192.168.1.100/ipp\n",
        )
        assert _discover_network_printer() == "192.168.1.100"

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_socket(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: socket://10.0.0.5:9100\n",
        )
        assert _discover_network_printer() == "10.0.0.5"

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_no_match(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: usb://Brother/HL-1110\n",
        )
        assert _discover_network_printer() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        assert _discover_network_printer() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_oserror(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert _discover_network_printer() == ""


class TestRunNetworkMode:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_snmpwalk(self, m: MagicMock) -> None:
        with (
            patch("sys.stdout", new_callable=StringIO),
            pytest.raises(SystemExit),
        ):
            _run_network_mode("1.2.3.4")

    @patch(f"{MOD}.display_network_results")
    @patch(f"{MOD}.query_network_snmp")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/snmpwalk")
    def test_success(
        self,
        w: MagicMock,
        mock_query: MagicMock,
        mock_display: MagicMock,
    ) -> None:
        from python_pkg.brother_printer.data_classes import NetworkResult

        mock_query.return_value = NetworkResult(ip="1.2.3.4")
        with patch("sys.stdout", new_callable=StringIO):
            _run_network_mode("1.2.3.4")
        mock_display.assert_called_once()


class TestRunUsbMode:
    @patch(f"{MOD}.display_usb_results")
    @patch(f"{MOD}.query_usb_pjl")
    def test_success(
        self,
        mock_query: MagicMock,
        mock_display: MagicMock,
    ) -> None:
        mock_query.return_value = USBResult()
        with patch("sys.stdout", new_callable=StringIO):
            _run_usb_mode("Brother USB line")
        mock_display.assert_called_once()


class TestNoPrinterFound:
    def test_exits(self) -> None:
        with (
            patch("sys.stdout", new_callable=StringIO),
            pytest.raises(SystemExit),
        ):
            _no_printer_found()

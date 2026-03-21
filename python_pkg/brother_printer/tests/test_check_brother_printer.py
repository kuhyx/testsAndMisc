"""Tests for brother_printer.check_brother_printer module."""

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
    main,
)

MOD = "python_pkg.brother_printer.check_brother_printer"


class TestDiscoverNetworkPrinter:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, _m: MagicMock) -> None:
        assert _discover_network_printer() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_found_ip(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: ipp://192.168.1.100/ipp\n",
        )
        assert _discover_network_printer() == "192.168.1.100"

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_socket(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: socket://10.0.0.5:9100\n",
        )
        assert _discover_network_printer() == "10.0.0.5"

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_no_match(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: usb://Brother/HL-1110\n",
        )
        assert _discover_network_printer() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        assert _discover_network_printer() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert _discover_network_printer() == ""


class TestRunNetworkMode:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_snmpwalk(self, _m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            with pytest.raises(SystemExit):
                _run_network_mode("1.2.3.4")

    @patch(f"{MOD}.display_network_results")
    @patch(f"{MOD}.query_network_snmp")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/snmpwalk")
    def test_success(
        self,
        _w: MagicMock,
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
        with patch("sys.stdout", new_callable=StringIO):
            with pytest.raises(SystemExit):
                _no_printer_found()


class TestMain:
    @patch(f"{MOD}.reset_consumable")
    def test_reset_toner(self, mock_reset: MagicMock) -> None:
        main(["--reset-toner"])
        mock_reset.assert_called_once_with("toner")

    @patch(f"{MOD}.reset_consumable")
    def test_reset_drum(self, mock_reset: MagicMock) -> None:
        main(["--reset-drum"])
        mock_reset.assert_called_once_with("drum")

    @patch(f"{MOD}.os.geteuid", return_value=1000)
    def test_not_root(self, _m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            with pytest.raises(SystemExit):
                main([])

    @patch(f"{MOD}._run_network_mode")
    @patch(f"{MOD}.os.geteuid", return_value=0)
    def test_with_ip(self, _g: MagicMock, mock_net: MagicMock) -> None:
        main(["1.2.3.4"])
        mock_net.assert_called_once_with("1.2.3.4")

    @patch(f"{MOD}._run_usb_mode")
    @patch(f"{MOD}.find_brother_usb", return_value="Brother USB")
    @patch(f"{MOD}.os.geteuid", return_value=0)
    def test_usb_found(
        self,
        _g: MagicMock,
        _f: MagicMock,
        mock_usb: MagicMock,
    ) -> None:
        main([])
        mock_usb.assert_called_once()

    @patch(f"{MOD}.display_network_results")
    @patch(f"{MOD}.query_network_snmp")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/snmpwalk")
    @patch(f"{MOD}._discover_network_printer", return_value="192.168.1.100")
    @patch(f"{MOD}.find_brother_usb", return_value="")
    @patch(f"{MOD}.os.geteuid", return_value=0)
    def test_network_discovered(
        self,
        _g: MagicMock,
        _f: MagicMock,
        _d: MagicMock,
        _w: MagicMock,
        mock_query: MagicMock,
        mock_display: MagicMock,
    ) -> None:
        from python_pkg.brother_printer.data_classes import NetworkResult

        mock_query.return_value = NetworkResult(ip="192.168.1.100")
        with patch("sys.stdout", new_callable=StringIO):
            main([])
        mock_display.assert_called_once()

    @patch(f"{MOD}._no_printer_found")
    @patch(f"{MOD}._discover_network_printer", return_value="")
    @patch(f"{MOD}.find_brother_usb", return_value="")
    @patch(f"{MOD}.os.geteuid", return_value=0)
    def test_nothing_found(
        self,
        _g: MagicMock,
        _f: MagicMock,
        _d: MagicMock,
        mock_no: MagicMock,
    ) -> None:
        main([])
        mock_no.assert_called_once()

    @patch(f"{MOD}._no_printer_found")
    @patch(f"{MOD}.shutil.which", return_value=None)
    @patch(f"{MOD}._discover_network_printer", return_value="192.168.1.100")
    @patch(f"{MOD}.find_brother_usb", return_value="")
    @patch(f"{MOD}.os.geteuid", return_value=0)
    def test_network_discovered_no_snmpwalk(
        self,
        _g: MagicMock,
        _f: MagicMock,
        _d: MagicMock,
        _w: MagicMock,
        mock_no: MagicMock,
    ) -> None:
        main([])
        mock_no.assert_called_once()

    def test_default_argv(self) -> None:
        with (
            patch(f"{MOD}.sys.argv", ["prog", "--reset-toner"]),
            patch(f"{MOD}.reset_consumable") as mock_reset,
        ):
            main()
            mock_reset.assert_called_once_with("toner")

    @patch(f"{MOD}.os.geteuid", return_value=1000)
    def test_not_root_with_args(self, _g: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            with pytest.raises(SystemExit):
                main(["1.2.3.4"])


from python_pkg.brother_printer.data_classes import USBResult

"""Tests for brother_printer.usb_query - discovery and PJL response parsing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.data_classes import USBResult
from python_pkg.brother_printer.usb_query import (
    _parse_status,
    _parse_variables,
    find_brother_usb,
    find_usb_printer_dev,
)

MOD = "python_pkg.brother_printer.usb_query"


class TestFindBrotherUsb:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lsusb(self, m: MagicMock) -> None:
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_found(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="Bus 001 Device 005: ID 04f9:0042 Brother Industries\n",
        )
        result = find_brother_usb()
        assert "Brother" in result

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_not_found(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="Bus 001 Device 001: Hub\n")
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_line_with_colon_sep(self, w: MagicMock, mock_run: MagicMock) -> None:
        """Line contains 04f9: but no ': ' separator → returns full line."""
        mock_run.return_value = MagicMock(stdout="ID 04f9:0042\n")
        result = find_brother_usb()
        assert result == "ID 04f9:0042"

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_no_match(self, w: MagicMock, mock_run: MagicMock) -> None:
        """Line without 04f9: vendor id is ignored."""
        mock_run.return_value = MagicMock(stdout="04f9 brother no colon\n")
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("lsusb", 5)
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_oserror(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert find_brother_usb() == ""


class TestFindUsbPrinterDev:
    @patch(f"{MOD}.Path")
    def test_found(self, mock_path_cls: MagicMock) -> None:
        mock_path_cls.return_value = mock_path_cls
        mock_path_cls.__truediv__ = lambda _self, _x: mock_path_cls
        lp0 = MagicMock()
        lp0.__str__ = lambda _s: "/dev/usb/lp0"
        lp0.__lt__ = lambda s, o: str(s) < str(o)
        mock_usb = MagicMock()
        mock_usb.glob.return_value = [lp0]
        mock_path_cls.side_effect = None
        with patch(f"{MOD}.Path", return_value=mock_usb):
            result = find_usb_printer_dev()
            assert result == "/dev/usb/lp0"

    @patch(f"{MOD}.Path")
    def test_not_found(self, mock_path_cls: MagicMock) -> None:
        mock_usb = MagicMock()
        mock_usb.glob.return_value = []
        mock_path_cls.return_value = mock_usb
        result = find_usb_printer_dev()
        assert result is None


class TestParseStatus:
    def test_found(self) -> None:
        result = USBResult()
        resp = 'CODE=10001\nDISPLAY= "Ready" \nONLINE=TRUE\n'
        assert _parse_status(resp, result) is True
        assert result.status_code == "10001"
        assert result.display == "Ready"
        assert result.online == "TRUE"

    def test_not_found(self) -> None:
        result = USBResult()
        assert _parse_status("nothing here\n", result) is False

    def test_partial(self) -> None:
        result = USBResult()
        resp = "DISPLAY=Hello\n"
        assert _parse_status(resp, result) is False
        assert result.display == "Hello"


class TestParseVariables:
    def test_found(self) -> None:
        result = USBResult()
        resp = "ECONOMODE=ON extra\n"
        assert _parse_variables(resp, result) is True
        assert result.economode == "ON"

    def test_not_found(self) -> None:
        result = USBResult()
        assert _parse_variables("nothing\n", result) is False

"""Tests for the shared brother_printer._query helpers."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer._query import (
    parse_cups_usb_uri,
    printer_info_from_cups,
    run_command_text,
)

MOD = "python_pkg.brother_printer._query"


class TestRunCommandText:
    """The shared subprocess wrapper."""

    @patch(f"{MOD}.subprocess.run")
    def test_returns_stdout(self, mock_run: MagicMock) -> None:
        """A successful run yields its captured stdout."""
        mock_run.return_value = MagicMock(stdout="line one\nline two\n")
        assert run_command_text(["echo", "hi"]) == "line one\nline two\n"

    @patch(f"{MOD}.subprocess.run")
    def test_timeout_is_empty(self, mock_run: MagicMock) -> None:
        """A timeout is swallowed and reported as empty output."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        assert run_command_text(["slow"]) == ""

    @patch(f"{MOD}.subprocess.run")
    def test_oserror_is_empty(self, mock_run: MagicMock) -> None:
        """An OS error (missing binary) is swallowed and reported as empty."""
        mock_run.side_effect = OSError("no such file")
        assert run_command_text(["missing"]) == ""

    @patch(f"{MOD}.subprocess.run")
    def test_subprocess_error_is_empty(self, mock_run: MagicMock) -> None:
        """A generic subprocess error is swallowed and reported as empty."""
        mock_run.side_effect = subprocess.SubprocessError("boom")
        assert run_command_text(["bad"]) == ""


class TestParseCupsUsbUri:
    """Parsing product/serial out of a CUPS ``usb://`` URI."""

    def test_full_uri(self) -> None:
        """A URI with a serial fills both product and serial."""
        info: dict[str, str] = {"product": "", "serial": ""}
        parse_cups_usb_uri("usb://Brother/HL-1110%20series?serial=ABC123", info)
        assert info["product"] == "HL-1110 series"
        assert info["serial"] == "ABC123"

    def test_no_serial(self) -> None:
        """A URI without a serial leaves the serial empty."""
        info: dict[str, str] = {"product": "", "serial": ""}
        parse_cups_usb_uri("usb://Brother/HL-1110", info)
        assert info["product"] == "HL-1110"
        assert info["serial"] == ""


class TestPrinterInfoFromCups:
    """Resolving model/serial from ``lpstat -v`` output."""

    @patch(f"{MOD}.run_command_text")
    def test_found(self, mock_text: MagicMock) -> None:
        """A Brother usb:// device line is parsed into product/serial."""
        mock_text.return_value = "device for B: usb://Brother/HL-1110?serial=XYZ\n"
        result = printer_info_from_cups()
        assert result["product"] == "HL-1110"
        assert result["serial"] == "XYZ"

    @patch(f"{MOD}.run_command_text")
    def test_no_brother(self, mock_text: MagicMock) -> None:
        """A non-Brother line yields no product."""
        mock_text.return_value = "device for HP: ipp://hp.local\n"
        assert printer_info_from_cups()["product"] == ""

    @patch(f"{MOD}.run_command_text")
    def test_brother_no_usb(self, mock_text: MagicMock) -> None:
        """A Brother line with no usb:// URI yields no product."""
        mock_text.return_value = "device for B: ipp://Brother.local\n"
        assert printer_info_from_cups()["product"] == ""

    @patch(f"{MOD}.run_command_text")
    def test_empty_output(self, mock_text: MagicMock) -> None:
        """No output (command failed) yields no product."""
        mock_text.return_value = ""
        assert printer_info_from_cups()["product"] == ""

"""Tests for brother_printer.cups_service module - part 4 (IPP queries)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    _get_cups_ipp_status,
    _parse_ipp_attributes,
)

MOD = "python_pkg.brother_printer.cups_service"


class TestParseIppAttributes:
    def test_parse(self) -> None:
        output = "  printer-state (enum) = idle\n  printer-name (name) = Brother\n"
        result = _parse_ipp_attributes(output)
        assert result["printer-state"] == "idle"
        assert result["printer-name"] == "Brother"

    def test_no_match(self) -> None:
        result = _parse_ipp_attributes("no attributes here\n")
        assert result == {}


class TestGetCupsIppStatus:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_ipptool(self, m: MagicMock) -> None:
        assert _get_cups_ipp_status("Brother") == {}

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/ipptool")
    def test_success(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="  printer-state (enum) = idle\n",
        )
        result = _get_cups_ipp_status("Brother")
        assert result["printer-state"] == "idle"

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/ipptool")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("ipptool", 10)
        assert _get_cups_ipp_status("Brother") == {}

"""Tests for brother_printer.cups_service module - part 4 (consumable life, IPP)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    _get_cups_ipp_status,
    _parse_ipp_attributes,
    estimate_consumable_life,
)

MOD = "python_pkg.brother_printer.cups_service"


class TestEstimateConsumableLife:
    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=0)
    def test_no_pages(self, p: MagicMock, mock_load: MagicMock) -> None:
        result = estimate_consumable_life()
        assert result.total_pages == 0

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=500)
    def test_mid_life(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {"toner_replaced_at": 0, "drum_replaced_at": 0}
        result = estimate_consumable_life()
        assert result.total_pages == 500
        assert result.toner_pct_remaining == 50
        assert result.toner_exhausted is False
        assert result.toner_low is False

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1000)
    def test_toner_exhausted(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {"toner_replaced_at": 0, "drum_replaced_at": 0}
        result = estimate_consumable_life()
        assert result.toner_exhausted is True

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=800)
    def test_toner_low(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {"toner_replaced_at": 0, "drum_replaced_at": 0}
        result = estimate_consumable_life()
        assert result.toner_low is True

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=9000)
    def test_drum_near_end(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {"toner_replaced_at": 8500, "drum_replaced_at": 0}
        result = estimate_consumable_life()
        assert result.drum_near_end is True


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

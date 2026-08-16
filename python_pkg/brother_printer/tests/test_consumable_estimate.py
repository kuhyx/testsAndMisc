"""Tests for brother_printer.consumables - the toner and drum life estimate.

Split from test_consumables.py under the 250-line cap. These cover which
counter the estimate is based on and how replacement resets rebase it.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.consumables import (
    STATE_SCHEMA_CUPS_SCALE,
    STATE_SCHEMA_PRINTER_SCALE,
    estimate_consumable_life,
    reset_consumable,
)

MOD = "python_pkg.brother_printer.consumables"


class TestEstimateConsumableLife:
    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=0)
    def test_no_pages(self, p: MagicMock, mock_load: MagicMock) -> None:
        result = estimate_consumable_life()
        assert result.total_pages == 0

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=500)
    def test_mid_life(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }
        result = estimate_consumable_life()
        assert result.total_pages == 500
        assert result.toner_pct_remaining == 50
        assert result.toner_exhausted is False
        assert result.toner_low is False

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1000)
    def test_toner_exhausted(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }
        result = estimate_consumable_life()
        assert result.toner_exhausted is True

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=800)
    def test_toner_low(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }
        result = estimate_consumable_life()
        assert result.toner_low is True

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=9000)
    def test_drum_near_end(self, p: MagicMock, mock_load: MagicMock) -> None:
        mock_load.return_value = {
            "toner_replaced_at": 8500,
            "drum_replaced_at": 0,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }
        result = estimate_consumable_life()
        assert result.drum_near_end is True


class TestEstimateConsumableLifeCounterSource:
    """Which counter the estimate came from, and whether it says so."""

    @patch(f"{MOD}._migrate_state_to_printer_scale")
    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1658)
    def test_printer_counter_is_authoritative(
        self,
        mock_cups: MagicMock,
        mock_load: MagicMock,
        mock_migrate: MagicMock,
    ) -> None:
        mock_load.return_value = {
            "toner_replaced_at": 1767,
            "drum_replaced_at": 0,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }
        mock_migrate.side_effect = lambda state, total: state
        estimate = estimate_consumable_life(2017)
        assert estimate.total_pages == 2017
        assert estimate.approximate is False
        assert estimate.toner_pages == 250

    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1658)
    def test_falls_back_to_cups_log_and_flags_it(
        self,
        mock_cups: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Without the printer's counter, say the number is approximate."""
        mock_load.return_value = {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }
        estimate = estimate_consumable_life(0)
        assert estimate.total_pages == 1658
        assert estimate.approximate is True

    @patch(f"{MOD}._get_cups_total_pages", return_value=0)
    def test_no_counter_at_all(self, mock_cups: MagicMock) -> None:
        assert estimate_consumable_life(0).total_pages == 0


class TestResetConsumableScale:
    @patch(f"{MOD}._out")
    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._load_consumable_state")
    def test_printer_total_marks_state_migrated(
        self,
        mock_load: MagicMock,
        mock_save: MagicMock,
        mock_out: MagicMock,
    ) -> None:
        """A baseline written from the printer is already on the new scale."""
        mock_load.return_value = {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_CUPS_SCALE,
        }
        reset_consumable("toner", 2017)
        saved = mock_save.call_args[0][0]
        assert saved["toner_replaced_at"] == 2017
        assert saved["schema"] == STATE_SCHEMA_PRINTER_SCALE

    @patch(f"{MOD}._out")
    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1658)
    def test_without_printer_total_uses_cups_log(
        self,
        mock_cups: MagicMock,
        mock_load: MagicMock,
        mock_save: MagicMock,
        mock_out: MagicMock,
    ) -> None:
        mock_load.return_value = {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_CUPS_SCALE,
        }
        reset_consumable("drum")
        saved = mock_save.call_args[0][0]
        assert saved["drum_replaced_at"] == 1658
        assert saved["schema"] == STATE_SCHEMA_CUPS_SCALE

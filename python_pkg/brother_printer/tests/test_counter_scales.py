"""Tests for brother_printer.consumables - rebasing the counter scales.

The printer's counter and the CUPS page log measure different things. These
tests pin the rebasing between them; the dropped-page detection that the gap
makes possible is covered in test_page_delivery.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.consumables import (
    STATE_SCHEMA_CUPS_SCALE,
    STATE_SCHEMA_PRINTER_SCALE,
    _cups_total_on_printer_scale,
    _migrate_state_to_printer_scale,
)

MOD = "python_pkg.brother_printer.consumables"


class TestMigrateStateToPrinterScale:
    """Rebasing replacement baselines from the CUPS page log onto the printer.

    The baselines are recorded against whatever counter was in use when they
    were written. Switching counters without rebasing them silently changes
    every reported percentage, so this is the migration that keeps the numbers
    meaning the same thing before and after.
    """

    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1658)
    def test_shifts_baseline_by_offset(
        self,
        mock_total: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        state = {
            "toner_replaced_at": 1408,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_CUPS_SCALE,
        }
        result = _migrate_state_to_printer_scale(state, 2017)
        # Offset is 2017 - 1658 = 359.
        assert result["toner_replaced_at"] == 1767
        assert result["schema"] == STATE_SCHEMA_PRINTER_SCALE
        mock_save.assert_called_once()

    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1658)
    def test_zero_baseline_left_alone(
        self,
        mock_total: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Zero means 'never replaced', not 'replaced at page zero'.

        On the printer's scale zero already means "as old as the printer",
        which is the truthful reading; shifting it would re-hide the pages the
        CUPS log never saw.
        """
        state = {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_CUPS_SCALE,
        }
        result = _migrate_state_to_printer_scale(state, 2017)
        assert result["drum_replaced_at"] == 0
        assert result["toner_replaced_at"] == 0

    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1658)
    def test_runs_only_once(
        self,
        mock_total: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """A second run must not shift the baselines again."""
        state = {
            "toner_replaced_at": 1767,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_PRINTER_SCALE,
        }
        result = _migrate_state_to_printer_scale(state, 2017)
        assert result["toner_replaced_at"] == 1767
        mock_save.assert_not_called()

    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=2100)
    def test_negative_offset_leaves_baselines(
        self,
        mock_total: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """If the CUPS log somehow exceeds the printer, do not corrupt state."""
        state = {
            "toner_replaced_at": 1408,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_CUPS_SCALE,
        }
        result = _migrate_state_to_printer_scale(state, 2017)
        assert result["toner_replaced_at"] == 1408
        assert result["schema"] == STATE_SCHEMA_PRINTER_SCALE


class TestCupsTotalOnPrinterScale:
    """The CUPS figure must be shifted onto the scale the baselines use.

    Without the shift the raw CUPS total sits below a printer-scale baseline,
    the subtraction clamps at zero, and a part-used cartridge reads 100%.
    """

    @patch(f"{MOD}._get_cups_total_pages", return_value=1778)
    def test_applies_offset(self, mock_cups: MagicMock) -> None:
        state = {"last_printer_count": 2087, "last_cups_total": 1778}
        assert _cups_total_on_printer_scale(state) == 2087

    @patch(f"{MOD}._get_cups_total_pages", return_value=1778)
    def test_no_snapshot_returns_raw(self, mock_cups: MagicMock) -> None:
        state = {"last_printer_count": 0, "last_cups_total": 0}
        assert _cups_total_on_printer_scale(state) == 1778

    @patch(f"{MOD}._get_cups_total_pages", return_value=1778)
    def test_negative_offset_returns_raw(self, mock_cups: MagicMock) -> None:
        state = {"last_printer_count": 1700, "last_cups_total": 1778}
        assert _cups_total_on_printer_scale(state) == 1778

    @patch(f"{MOD}._get_cups_total_pages", return_value=0)
    def test_no_cups_pages(self, mock_cups: MagicMock) -> None:
        state = {"last_printer_count": 2087, "last_cups_total": 1778}
        assert _cups_total_on_printer_scale(state) == 0

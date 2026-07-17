"""Tests for brother_printer.consumables - state, estimates, resets."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.consumables import (
    STATE_SCHEMA_CUPS_SCALE,
    STATE_SCHEMA_PRINTER_SCALE,
    _get_cups_total_pages,
    _load_consumable_state,
    _save_consumable_state,
    estimate_consumable_life,
    reset_consumable,
)

MOD = "python_pkg.brother_printer.consumables"


class TestGetCupsTotalPages:
    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_no_log(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = False
        assert _get_cups_total_pages() == 0

    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_with_entries(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = True
        mock_log.read_text.return_value = (
            "printer 1 [2025-01-01] total 5\n"
            "printer 2 [2025-01-01] total 3\n"
            "printer 1 [2025-01-01] total 10\n"
        )
        assert _get_cups_total_pages() == 13  # max(5,10) + 3

    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_oserror(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = True
        mock_log.read_text.side_effect = OSError("fail")
        assert _get_cups_total_pages() == 0

    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_no_matching_lines(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = True
        mock_log.read_text.return_value = "some garbage\n"
        assert _get_cups_total_pages() == 0


class TestLoadConsumableState:
    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_no_file(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = False
        result = _load_consumable_state()
        assert result == {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_CUPS_SCALE,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_valid_file(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps(
            {"toner_replaced_at": 100, "drum_replaced_at": 200},
        )
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 100
        assert result["drum_replaced_at"] == 200

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_oserror(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.side_effect = OSError("fail")
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 0

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_bad_json(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "not json"
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 0

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_bad_values(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps(
            {"toner_replaced_at": "bad"},
        )
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 0


class TestSaveConsumableState:
    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_saves(self, mock_file: MagicMock) -> None:
        mock_file.parent = MagicMock()
        _save_consumable_state({"toner_replaced_at": 100, "drum_replaced_at": 200})
        mock_file.write_text.assert_called_once()
        written = mock_file.write_text.call_args[0][0]
        data = json.loads(written)
        assert data["toner_replaced_at"] == 100


class TestResetConsumable:
    @patch(f"{MOD}._out")
    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=500)
    def test_reset_toner(
        self,
        pages: MagicMock,
        load: MagicMock,
        mock_save: MagicMock,
        out: MagicMock,
    ) -> None:
        load.return_value = {"toner_replaced_at": 0, "drum_replaced_at": 0}
        reset_consumable("toner")
        saved_state = mock_save.call_args[0][0]
        assert saved_state["toner_replaced_at"] == 500


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

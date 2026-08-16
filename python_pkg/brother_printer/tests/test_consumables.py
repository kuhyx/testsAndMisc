"""Tests for brother_printer.consumables - the state file and page log."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.consumables import (
    STATE_SCHEMA_CUPS_SCALE,
    _get_cups_total_pages,
    _load_consumable_state,
    _save_consumable_state,
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

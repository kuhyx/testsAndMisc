"""Tests for brother_printer.consumables - counter scales and dropped pages.

The printer's counter and the CUPS page log measure different things. These
tests pin the rebasing between them and the dropped-page detection that the
gap makes possible.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.consumables import (
    STATE_SCHEMA_CUPS_SCALE,
    STATE_SCHEMA_PRINTER_SCALE,
    _cups_total_on_printer_scale,
    _migrate_state_to_printer_scale,
    _snapshot_counters,
    check_page_delivery,
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


class TestCheckPageDelivery:
    """Spotting pages the printer silently dropped.

    CUPS calls a job successful once the data leaves the machine, so this
    comparison against the printer's own counter is the only signal that a page
    never actually came out.
    """

    @patch(f"{MOD}._snapshot_counters")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1841)
    @patch(f"{MOD}._load_consumable_state")
    def test_detects_dropped_pages(
        self,
        mock_load: MagicMock,
        mock_cups: MagicMock,
        mock_snap: MagicMock,
    ) -> None:
        """Replay of the real failure: CUPS sent 63, printer printed none."""
        mock_load.return_value = {
            "last_printer_count": 2087,
            "last_cups_total": 1778,
        }
        check = check_page_delivery(2087, queue_idle=True)
        assert check.cups_pages == 63
        assert check.printer_pages == 0
        assert check.dropped == 63
        assert check.suspected is True

    @patch(f"{MOD}._snapshot_counters")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1841)
    @patch(f"{MOD}._load_consumable_state")
    def test_healthy_job_does_not_warn(
        self,
        mock_load: MagicMock,
        mock_cups: MagicMock,
        mock_snap: MagicMock,
    ) -> None:
        mock_load.return_value = {
            "last_printer_count": 2024,
            "last_cups_total": 1778,
        }
        check = check_page_delivery(2087, queue_idle=True)
        assert check.dropped == 0
        assert check.suspected is False

    @patch(f"{MOD}._snapshot_counters")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1780)
    @patch(f"{MOD}._load_consumable_state")
    def test_small_gap_is_not_a_warning(
        self,
        mock_load: MagicMock,
        mock_cups: MagicMock,
        mock_snap: MagicMock,
    ) -> None:
        """A page or two of drift is timing, not a fault."""
        mock_load.return_value = {
            "last_printer_count": 2087,
            "last_cups_total": 1778,
        }
        check = check_page_delivery(2087, queue_idle=True)
        assert check.dropped == 2
        assert check.suspected is False

    def test_skipped_while_printing(self) -> None:
        """Mid-job the counters legitimately disagree, so never compare."""
        assert check_page_delivery(2087, queue_idle=False).suspected is False

    def test_skipped_without_printer_count(self) -> None:
        assert check_page_delivery(0, queue_idle=True).suspected is False

    @patch(f"{MOD}._snapshot_counters")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1841)
    @patch(f"{MOD}._load_consumable_state")
    def test_first_run_only_establishes_baseline(
        self,
        mock_load: MagicMock,
        mock_cups: MagicMock,
        mock_snap: MagicMock,
    ) -> None:
        mock_load.return_value = {"last_printer_count": 0, "last_cups_total": 0}
        check = check_page_delivery(2087, queue_idle=True)
        assert check.suspected is False
        mock_snap.assert_called_once()

    @patch(f"{MOD}._snapshot_counters")
    @patch(f"{MOD}._get_cups_total_pages", return_value=10)
    @patch(f"{MOD}._load_consumable_state")
    def test_log_rotation_draws_no_conclusion(
        self,
        mock_load: MagicMock,
        mock_cups: MagicMock,
        mock_snap: MagicMock,
    ) -> None:
        """A rotated page log makes the delta negative; do not cry wolf."""
        mock_load.return_value = {
            "last_printer_count": 2087,
            "last_cups_total": 1778,
        }
        check = check_page_delivery(2087, queue_idle=True)
        assert check.suspected is False

    @patch(f"{MOD}._snapshot_counters")
    @patch(f"{MOD}._get_cups_total_pages", return_value=1841)
    @patch(f"{MOD}._load_consumable_state")
    def test_printer_counter_reset_draws_no_conclusion(
        self,
        mock_load: MagicMock,
        mock_cups: MagicMock,
        mock_snap: MagicMock,
    ) -> None:
        mock_load.return_value = {
            "last_printer_count": 5000,
            "last_cups_total": 1778,
        }
        check = check_page_delivery(2087, queue_idle=True)
        assert check.suspected is False


class TestSnapshotCounters:
    @patch(f"{MOD}._save_consumable_state")
    def test_writes_new_snapshot(self, mock_save: MagicMock) -> None:
        state = {"last_printer_count": 2000, "last_cups_total": 1700}
        _snapshot_counters(state, 2087, 1778)
        saved = mock_save.call_args[0][0]
        assert saved["last_printer_count"] == 2087
        assert saved["last_cups_total"] == 1778

    @patch(f"{MOD}._save_consumable_state")
    def test_unchanged_counters_skip_the_write(self, mock_save: MagicMock) -> None:
        """Do not rewrite the file on every run when nothing moved."""
        state = {"last_printer_count": 2087, "last_cups_total": 1778}
        _snapshot_counters(state, 2087, 1778)
        mock_save.assert_not_called()


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

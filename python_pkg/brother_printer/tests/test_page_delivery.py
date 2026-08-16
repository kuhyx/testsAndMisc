"""Tests for brother_printer._page_delivery - dropped-page detection.

Split from test_consumables_part2.py under the 250-line cap. These are exactly
the tests whose functions moved to _page_delivery, so the file needs only that
module's patch target rather than the two constants the combined file carried.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer._page_delivery import (
    _snapshot_counters,
    check_page_delivery,
)

MOD = "python_pkg.brother_printer._page_delivery"


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

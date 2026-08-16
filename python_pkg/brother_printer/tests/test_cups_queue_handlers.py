"""Tests for brother_printer._queue_fix - the choice dispatchers.

Split from test_cups_queue_part2.py under the 250-line cap. Each dispatcher
maps a menu choice onto the CUPS action primitives, which are patched on
_queue_fix because that is the module whose globals they resolve through.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer._queue_fix import (
    _handle_backend_errors_only,
    _handle_disabled_no_jobs,
    _handle_disabled_with_jobs,
    _handle_enabled_with_jobs,
)
from python_pkg.brother_printer.data_classes import CUPSJob, CUPSQueueStatus

MOD = "python_pkg.brother_printer._queue_fix"


class TestHandleDisabledWithJobs:
    """Tests for _handle_disabled_with_jobs dispatch."""

    def _make_queue(self) -> CUPSQueueStatus:
        return CUPSQueueStatus(
            printer_name="B",
            enabled=False,
            jobs=[CUPSJob("j1", "alice", "1024", "Mon")],
        )

    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    def test_choice_1(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_with_jobs(self._make_queue(), "1")

    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=True)
    def test_choice_2(self, c: MagicMock, e: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_with_jobs(self._make_queue(), "2")

    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=True)
    def test_choice_3(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_with_jobs(self._make_queue(), "3")

    @patch(f"{MOD}._cups_restart_service", return_value=True)
    def test_choice_4(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_with_jobs(self._make_queue(), "4")

    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    @patch(f"{MOD}._cups_restart_service", return_value=True)
    def test_choice_5(self, r: MagicMock, e: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_with_jobs(self._make_queue(), "5")

    def test_choice_6_no_action(self) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_with_jobs(self._make_queue(), "6")

    def test_invalid_choice(self) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_with_jobs(self._make_queue(), "99")


# ── _handle_disabled_no_jobs ─────────────────────────────────────────


class TestHandleDisabledNoJobs:
    """Tests for _handle_disabled_no_jobs."""

    def _make_queue(self) -> CUPSQueueStatus:
        return CUPSQueueStatus(printer_name="B", enabled=False)

    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    def test_choice_1_enable(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_no_jobs(self._make_queue(), "1")

    @patch(f"{MOD}._cups_enable_printer", return_value=False)
    def test_choice_1_enable_fails(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_no_jobs(self._make_queue(), "1")

    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    @patch(f"{MOD}._cups_restart_service", return_value=True)
    def test_choice_2_restart(self, r: MagicMock, e: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_no_jobs(self._make_queue(), "2")

    @patch(f"{MOD}._cups_restart_service", return_value=False)
    def test_choice_2_restart_fails(self, r: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_no_jobs(self._make_queue(), "2")

    def test_choice_3_no_action(self) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_disabled_no_jobs(self._make_queue(), "3")


# ── _handle_enabled_with_jobs ────────────────────────────────────────


class TestHandleEnabledWithJobs:
    """Tests for _handle_enabled_with_jobs."""

    def _make_queue(self) -> CUPSQueueStatus:
        return CUPSQueueStatus(
            printer_name="B",
            enabled=True,
            jobs=[CUPSJob("j1", "alice", "1024", "Mon")],
        )

    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=True)
    def test_choice_1_cancel(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_enabled_with_jobs(self._make_queue(), "1")

    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=False)
    def test_choice_1_cancel_fails(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_enabled_with_jobs(self._make_queue(), "1")

    @patch(f"{MOD}._cups_restart_service", return_value=True)
    def test_choice_2_restart(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_enabled_with_jobs(self._make_queue(), "2")

    @patch(f"{MOD}._cups_restart_service", return_value=False)
    def test_choice_2_restart_fails(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_enabled_with_jobs(self._make_queue(), "2")

    def test_choice_3_no_action(self) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_enabled_with_jobs(self._make_queue(), "3")


# ── _handle_backend_errors_only ──────────────────────────────────────


class TestHandleBackendErrorsOnly:
    """Tests for _handle_backend_errors_only."""

    @patch(f"{MOD}._cups_restart_service", return_value=True)
    def test_choice_1_restart(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_backend_errors_only("1")

    @patch(f"{MOD}._cups_restart_service", return_value=False)
    def test_choice_1_restart_fails(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_backend_errors_only("1")

    def test_choice_2_no_action(self) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _handle_backend_errors_only("2")

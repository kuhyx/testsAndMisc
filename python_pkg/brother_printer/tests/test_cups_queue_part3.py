"""Tests for brother_printer.cups_queue module - part 3 (display status)."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_queue import (
    display_cups_queue_status,
)
from python_pkg.brother_printer.data_classes import CUPSJob, CUPSQueueStatus

MOD = "python_pkg.brother_printer.cups_queue"


class TestDisplayCupsQueueStatus:
    def test_no_printer(self) -> None:
        queue = CUPSQueueStatus(printer_name="")
        with patch("sys.stdout", new_callable=StringIO) as out:
            display_cups_queue_status(queue)
            assert out.getvalue() == ""

    def test_all_ok(self) -> None:
        queue = CUPSQueueStatus(
            printer_name="B",
            enabled=True,
            jobs=[],
            has_backend_errors=False,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            display_cups_queue_status(queue)
            assert out.getvalue() == ""

    @patch(f"{MOD}._offer_queue_fix")
    def test_disabled(self, mock_fix: MagicMock) -> None:
        queue = CUPSQueueStatus(
            printer_name="B",
            enabled=False,
            reason="paused",
        )
        with patch("sys.stdout", new_callable=StringIO):
            display_cups_queue_status(queue)
        mock_fix.assert_called_once()

    @patch(f"{MOD}._offer_queue_fix")
    def test_with_jobs(self, mock_fix: MagicMock) -> None:
        queue = CUPSQueueStatus(
            printer_name="B",
            enabled=True,
            jobs=[CUPSJob("j1", "alice", "1024", "Mon")],
        )
        with patch("sys.stdout", new_callable=StringIO):
            display_cups_queue_status(queue)
        mock_fix.assert_called_once()

    @patch(f"{MOD}._offer_queue_fix")
    def test_backend_errors_only(self, mock_fix: MagicMock) -> None:
        queue = CUPSQueueStatus(
            printer_name="B",
            enabled=True,
            has_backend_errors=True,
        )
        with patch("sys.stdout", new_callable=StringIO):
            display_cups_queue_status(queue)
        mock_fix.assert_called_once()

    @patch(f"{MOD}._offer_queue_fix")
    def test_disabled_no_reason(self, mock_fix: MagicMock) -> None:
        queue = CUPSQueueStatus(
            printer_name="B",
            enabled=False,
            reason="",
        )
        with patch("sys.stdout", new_callable=StringIO):
            display_cups_queue_status(queue)
        mock_fix.assert_called_once()

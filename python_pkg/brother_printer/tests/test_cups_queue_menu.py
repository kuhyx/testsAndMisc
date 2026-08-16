"""Tests for brother_printer._queue_fix - the interactive fix menu."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer._queue_fix import (
    _dwj_cancel_and_enable,
    _dwj_cancel_only,
    _dwj_enable_only,
    _dwj_restart_and_enable,
    _dwj_restart_only,
    _offer_queue_fix,
)
from python_pkg.brother_printer.data_classes import CUPSJob, CUPSQueueStatus

MOD = "python_pkg.brother_printer._queue_fix"


# ── _offer_queue_fix ─────────────────────────────────────────────────


class TestOfferQueueFix:
    """Tests for _offer_queue_fix menu routing."""

    @patch(f"{MOD}._handle_disabled_with_jobs")
    @patch(f"{MOD}._prompt", return_value="1")
    def test_disabled_with_jobs(self, p: MagicMock, mock_handler: MagicMock) -> None:
        queue = CUPSQueueStatus(
            printer_name="B",
            enabled=False,
            jobs=[CUPSJob("j1", "alice", "1024", "Mon")],
        )
        with patch("sys.stdout", new_callable=StringIO):
            _offer_queue_fix(queue)
        mock_handler.assert_called_once_with(queue, "1")

    @patch(f"{MOD}._handle_disabled_no_jobs")
    @patch(f"{MOD}._prompt", return_value="2")
    def test_disabled_no_jobs(self, p: MagicMock, mock_handler: MagicMock) -> None:
        queue = CUPSQueueStatus(printer_name="B", enabled=False)
        with patch("sys.stdout", new_callable=StringIO):
            _offer_queue_fix(queue)
        mock_handler.assert_called_once_with(queue, "2")

    @patch(f"{MOD}._handle_enabled_with_jobs")
    @patch(f"{MOD}._prompt", return_value="1")
    def test_enabled_with_jobs(self, p: MagicMock, mock_handler: MagicMock) -> None:
        queue = CUPSQueueStatus(
            printer_name="B",
            enabled=True,
            jobs=[CUPSJob("j1", "alice", "1024", "Mon")],
        )
        with patch("sys.stdout", new_callable=StringIO):
            _offer_queue_fix(queue)
        mock_handler.assert_called_once_with(queue, "1")

    @patch(f"{MOD}._handle_backend_errors_only")
    @patch(f"{MOD}._prompt", return_value="1")
    def test_backend_errors_only(self, p: MagicMock, mock_handler: MagicMock) -> None:
        queue = CUPSQueueStatus(printer_name="B", enabled=True)
        with patch("sys.stdout", new_callable=StringIO):
            _offer_queue_fix(queue)
        mock_handler.assert_called_once_with("1")


# ── _dwj_* action functions ─────────────────────────────────────────


class TestDwjEnableOnly:
    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    def test_success(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_enable_only("B")

    @patch(f"{MOD}._cups_enable_printer", return_value=False)
    def test_failure(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_enable_only("B")


class TestDwjCancelAndEnable:
    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=True)
    def test_success(self, c: MagicMock, e: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_cancel_and_enable("B")

    @patch(f"{MOD}._cups_enable_printer", return_value=False)
    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=True)
    def test_enable_fails(self, c: MagicMock, e: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_cancel_and_enable("B")


class TestDwjCancelOnly:
    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=True)
    def test_success(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_cancel_only("B")

    @patch(f"{MOD}._cups_cancel_all_jobs", return_value=False)
    def test_failure(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_cancel_only("B")


class TestDwjRestartOnly:
    @patch(f"{MOD}._cups_restart_service", return_value=True)
    def test_success(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_restart_only("B")

    @patch(f"{MOD}._cups_restart_service", return_value=False)
    def test_failure(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_restart_only("B")


class TestDwjRestartAndEnable:
    @patch(f"{MOD}._cups_enable_printer", return_value=True)
    @patch(f"{MOD}._cups_restart_service", return_value=True)
    def test_success(self, r: MagicMock, e: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_restart_and_enable("B")

    @patch(f"{MOD}._cups_restart_service", return_value=False)
    def test_restart_fails(self, r: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            _dwj_restart_and_enable("B")

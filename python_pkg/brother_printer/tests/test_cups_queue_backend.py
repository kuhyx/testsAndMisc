"""Tests for brother_printer.cups_queue - stale backend error detection.

Split from test_cups_queue.py under the 250-line cap.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_queue import (
    _check_cups_backend_errors,
    _find_backend_error_in_log,
    _is_cups_printer_healthy,
)

MOD = "python_pkg.brother_printer.cups_queue"


class TestIsCupsPrinterHealthy:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, m: MagicMock) -> None:
        assert _is_cups_printer_healthy("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_healthy(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="printer BrotherHL1110 is idle.  enabled since Mon\n",
        )
        assert _is_cups_printer_healthy("BrotherHL1110") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_not_healthy(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="printer BrotherHL1110 disabled\n",
        )
        assert _is_cups_printer_healthy("BrotherHL1110") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        assert _is_cups_printer_healthy("B") is False


class TestFindBackendErrorInLog:
    def test_no_errors(self) -> None:
        lines = ["[2025-01-01] Completed job\n"]
        err, _, _ = _find_backend_error_in_log(lines)
        assert err == ""

    def test_backend_error(self) -> None:
        lines = [
            "[2025-01-01] Completed job",
            "[2025-01-02] backend errors for BrotherHL1110",
        ]
        err, ts, success_ts = _find_backend_error_in_log(lines)
        assert "backend errors" in err
        assert ts == "2025-01-02"
        assert success_ts == "2025-01-01"

    def test_stopped_with_status(self) -> None:
        lines = [
            "[2025-01-02] stopped with status 1",
        ]
        err, ts, _ = _find_backend_error_in_log(lines)
        assert "stopped with status" in err
        assert ts == "2025-01-02"

    def test_error_no_timestamp(self) -> None:
        lines = ["backend errors no timestamp here"]
        err, ts, _ = _find_backend_error_in_log(lines)
        assert "backend errors" in err
        assert ts == ""

    def test_completed_with_total(self) -> None:
        lines = [
            "[2025-01-01] page total 10",
            "[2025-01-02] backend errors",
        ]
        _, _, success_ts = _find_backend_error_in_log(lines)
        assert success_ts == "2025-01-01"

    def test_no_success_after_error(self) -> None:
        lines = [
            "[2025-01-02] backend errors",
        ]
        _, _, success_ts = _find_backend_error_in_log(lines)
        assert success_ts == ""

    def test_completed_no_timestamp(self) -> None:
        lines = [
            "Completed job",
            "[2025-01-02] backend errors",
        ]
        _, _, success_ts = _find_backend_error_in_log(lines)
        assert success_ts == ""


class TestCheckCupsBackendErrors:
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=True)
    def test_healthy_printer(self, m: MagicMock) -> None:
        has_errors, _ = _check_cups_backend_errors("B")
        assert has_errors is False

    @patch(f"{MOD}._find_backend_error_in_log", return_value=("", "", ""))
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_no_log_file(self, h: MagicMock, f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = False
            mock_path.return_value = mock_log
            has_errors, _ = _check_cups_backend_errors("B")
            assert has_errors is False

    @patch(
        f"{MOD}._find_backend_error_in_log", return_value=("error", "2025-01-02", "")
    )
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_has_errors(self, h: MagicMock, f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.return_value = "log content"
            mock_path.return_value = mock_log
            has_errors, _ = _check_cups_backend_errors("B")
            assert has_errors is True

    @patch(
        f"{MOD}._find_backend_error_in_log",
        return_value=("error", "2025-01-01", "2025-01-02"),
    )
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_success_after_error(self, h: MagicMock, f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.return_value = "log content"
            mock_path.return_value = mock_log
            has_errors, _ = _check_cups_backend_errors("B")
            assert has_errors is False

    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_oserror_reading_log(self, h: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.side_effect = OSError("fail")
            mock_path.return_value = mock_log
            has_errors, _ = _check_cups_backend_errors("B")
            assert has_errors is False

    @patch(f"{MOD}._find_backend_error_in_log", return_value=("", "", ""))
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_no_backend_error_in_log(self, h: MagicMock, f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.return_value = "clean log"
            mock_path.return_value = mock_log
            has_errors, _ = _check_cups_backend_errors("B")
            assert has_errors is False

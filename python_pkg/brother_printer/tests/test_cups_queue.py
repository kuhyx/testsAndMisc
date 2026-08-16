"""Tests for brother_printer.cups_queue module."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_queue import (
    _parse_lpstat_jobs,
    _parse_lpstat_printer_line,
    get_cups_queue_status,
)

MOD = "python_pkg.brother_printer.cups_queue"


class TestParseLpstatPrinterLine:
    def test_enabled(self) -> None:
        enabled, reason = _parse_lpstat_printer_line(
            "printer BrotherHL1110 is idle.  enabled since Mon 01 2025 - ok",
        )
        assert enabled is True
        assert reason == "ok"

    def test_disabled(self) -> None:
        enabled, reason = _parse_lpstat_printer_line(
            "printer BrotherHL1110 disabled since Mon 01 2025 - paused",
        )
        assert enabled is False
        assert reason == "paused"

    def test_no_reason(self) -> None:
        enabled, reason = _parse_lpstat_printer_line(
            "printer BrotherHL1110 is idle.",
        )
        assert enabled is True
        assert reason == ""


class TestParseLpstatJobs:
    def test_parse_jobs(self) -> None:
        output = (
            "BrotherHL1110-1 alice 1024 Mon 01 2025\n"
            "BrotherHL1110-2 bob 2048 Tue 02 2025\n"
            "HP-1 charlie 512 Wed 03 2025\n"
        )
        jobs = _parse_lpstat_jobs(output, "BrotherHL1110")
        assert len(jobs) == 2
        assert jobs[0].job_id == "BrotherHL1110-1"
        assert jobs[0].user == "alice"

    def test_too_few_parts(self) -> None:
        output = "BrotherHL1110-1 alice 1024\n"
        jobs = _parse_lpstat_jobs(output, "BrotherHL1110")
        assert len(jobs) == 0


class TestGetCupsQueueStatus:
    @patch(f"{MOD}.find_cups_printer_name", return_value="")
    def test_no_printer(self, f: MagicMock) -> None:
        result = get_cups_queue_status()
        assert result.printer_name == ""

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(False, ""))
    @patch(f"{MOD}.shutil.which", return_value=None)
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_no_lpstat(self, f: MagicMock, w: MagicMock, c: MagicMock) -> None:
        result = get_cups_queue_status()
        assert result.printer_name == "BrotherHL1110"

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(False, ""))
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_full_status(
        self,
        f: MagicMock,
        w: MagicMock,
        mock_run: MagicMock,
        c: MagicMock,
    ) -> None:
        # First call for printer status, second for jobs
        mock_run.side_effect = [
            MagicMock(
                stdout=(
                    "printer BrotherHL1110 is idle.  enabled since Mon 01 2025 - ok\n"
                ),
            ),
            MagicMock(
                stdout="BrotherHL1110-1 alice 1024 Mon 01 2025\n",
            ),
        ]
        result = get_cups_queue_status()
        assert result.enabled is True
        assert len(result.jobs) == 1

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(True, "backend error"))
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_with_backend_errors(
        self,
        f: MagicMock,
        w: MagicMock,
        mock_run: MagicMock,
        c: MagicMock,
    ) -> None:
        mock_run.side_effect = [
            MagicMock(stdout="printer BrotherHL1110 disabled\n"),
            MagicMock(stdout=""),
        ]
        result = get_cups_queue_status()
        assert result.has_backend_errors is True

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(False, ""))
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_printer_status_timeout(
        self,
        f: MagicMock,
        w: MagicMock,
        mock_run: MagicMock,
        c: MagicMock,
    ) -> None:
        mock_run.side_effect = [
            subprocess.TimeoutExpired("lpstat", 5),
            MagicMock(stdout=""),
        ]
        result = get_cups_queue_status()
        assert result.enabled is True  # default

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(False, ""))
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_job_status_timeout(
        self,
        f: MagicMock,
        w: MagicMock,
        mock_run: MagicMock,
        c: MagicMock,
    ) -> None:
        mock_run.side_effect = [
            MagicMock(stdout=""),
            subprocess.TimeoutExpired("lpstat", 5),
        ]
        result = get_cups_queue_status()
        assert result.jobs == []

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(False, ""))
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_no_matching_printer_line(
        self,
        f: MagicMock,
        w: MagicMock,
        mock_run: MagicMock,
        c: MagicMock,
    ) -> None:
        mock_run.side_effect = [
            MagicMock(stdout="printer HP is idle.\n"),
            MagicMock(stdout=""),
        ]
        result = get_cups_queue_status()
        assert result.enabled is True  # default unchanged

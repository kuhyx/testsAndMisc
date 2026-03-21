"""Tests for brother_printer.cups_queue module."""

from __future__ import annotations

from io import StringIO
import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_queue import (
    _check_cups_backend_errors,
    _cups_cancel_all_jobs,
    _cups_cancel_job,
    _cups_enable_printer,
    _cups_restart_service,
    _find_backend_error_in_log,
    _is_cups_printer_healthy,
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
    def test_no_printer(self, _f: MagicMock) -> None:
        result = get_cups_queue_status()
        assert result.printer_name == ""

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(False, ""))
    @patch(f"{MOD}.shutil.which", return_value=None)
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_no_lpstat(self, _f: MagicMock, _w: MagicMock, _c: MagicMock) -> None:
        result = get_cups_queue_status()
        assert result.printer_name == "BrotherHL1110"

    @patch(f"{MOD}._check_cups_backend_errors", return_value=(False, ""))
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    @patch(f"{MOD}.find_cups_printer_name", return_value="BrotherHL1110")
    def test_full_status(
        self,
        _f: MagicMock,
        _w: MagicMock,
        mock_run: MagicMock,
        _c: MagicMock,
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
        _f: MagicMock,
        _w: MagicMock,
        mock_run: MagicMock,
        _c: MagicMock,
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
        _f: MagicMock,
        _w: MagicMock,
        mock_run: MagicMock,
        _c: MagicMock,
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
        _f: MagicMock,
        _w: MagicMock,
        mock_run: MagicMock,
        _c: MagicMock,
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
        _f: MagicMock,
        _w: MagicMock,
        mock_run: MagicMock,
        _c: MagicMock,
    ) -> None:
        mock_run.side_effect = [
            MagicMock(stdout="printer HP is idle.\n"),
            MagicMock(stdout=""),
        ]
        result = get_cups_queue_status()
        assert result.enabled is True  # default unchanged


class TestCupsEnablePrinter:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_cupsenable(self, _m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_enable_printer("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cupsenable")
    def test_success(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _cups_enable_printer("B") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cupsenable")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("cupsenable", 5)
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_enable_printer("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cupsenable")
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_enable_printer("B") is False


class TestCupsCancelAllJobs:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_cancel(self, _m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_cancel_all_jobs("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_success(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _cups_cancel_all_jobs("B") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_error(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "cancel")
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_cancel_all_jobs("B") is False


class TestCupsCancelJob:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_cancel(self, _m: MagicMock) -> None:
        assert _cups_cancel_job("job-1") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_success(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _cups_cancel_job("job-1") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_error(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "cancel")
        assert _cups_cancel_job("job-1") is False


class TestCupsRestartService:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_systemctl(self, _m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_restart_service() is False

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.time.time")
    @patch(f"{MOD}.subprocess.Popen")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_success(
        self,
        _w: MagicMock,
        mock_popen: MagicMock,
        mock_time: MagicMock,
        _s: MagicMock,
    ) -> None:
        proc = MagicMock()
        proc.poll.side_effect = [None, 0]
        proc.returncode = 0
        mock_popen.return_value = proc
        mock_time.side_effect = [0.0, 1.0, 2.0]
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_restart_service() is True

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.time.time")
    @patch(f"{MOD}.subprocess.Popen")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_timeout(
        self,
        _w: MagicMock,
        mock_popen: MagicMock,
        mock_time: MagicMock,
        _s: MagicMock,
    ) -> None:
        proc = MagicMock()
        proc.poll.return_value = None
        mock_popen.return_value = proc
        mock_time.side_effect = [0.0, 31.0]
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_restart_service() is False
            proc.kill.assert_called_once()

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.time.time")
    @patch(f"{MOD}.subprocess.Popen")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_nonzero_exit(
        self,
        _w: MagicMock,
        mock_popen: MagicMock,
        mock_time: MagicMock,
        _s: MagicMock,
    ) -> None:
        proc = MagicMock()
        proc.poll.side_effect = [None, 1]
        proc.returncode = 1
        mock_popen.return_value = proc
        mock_time.side_effect = [0.0, 1.0, 2.0]
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_restart_service() is False

    @patch(f"{MOD}.subprocess.Popen")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_oserror(self, _w: MagicMock, mock_popen: MagicMock) -> None:
        mock_popen.side_effect = OSError("fail")
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_restart_service() is False


class TestIsCupsPrinterHealthy:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, _m: MagicMock) -> None:
        assert _is_cups_printer_healthy("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_healthy(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="printer BrotherHL1110 is idle.  enabled since Mon\n",
        )
        assert _is_cups_printer_healthy("BrotherHL1110") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_not_healthy(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="printer BrotherHL1110 disabled\n",
        )
        assert _is_cups_printer_healthy("BrotherHL1110") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        assert _is_cups_printer_healthy("B") is False


class TestFindBackendErrorInLog:
    def test_no_errors(self) -> None:
        lines = ["[2025-01-01] Completed job\n"]
        err, ts, success_ts = _find_backend_error_in_log(lines)
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
        err, ts, success_ts = _find_backend_error_in_log(lines)
        assert "stopped with status" in err
        assert ts == "2025-01-02"

    def test_error_no_timestamp(self) -> None:
        lines = ["backend errors no timestamp here"]
        err, ts, success_ts = _find_backend_error_in_log(lines)
        assert "backend errors" in err
        assert ts == ""

    def test_completed_with_total(self) -> None:
        lines = [
            "[2025-01-01] page total 10",
            "[2025-01-02] backend errors",
        ]
        err, ts, success_ts = _find_backend_error_in_log(lines)
        assert success_ts == "2025-01-01"

    def test_no_success_after_error(self) -> None:
        lines = [
            "[2025-01-02] backend errors",
        ]
        err, ts, success_ts = _find_backend_error_in_log(lines)
        assert success_ts == ""

    def test_completed_no_timestamp(self) -> None:
        lines = [
            "Completed job",
            "[2025-01-02] backend errors",
        ]
        err, ts, success_ts = _find_backend_error_in_log(lines)
        assert success_ts == ""


class TestCheckCupsBackendErrors:
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=True)
    def test_healthy_printer(self, _m: MagicMock) -> None:
        has_errors, msg = _check_cups_backend_errors("B")
        assert has_errors is False

    @patch(f"{MOD}._find_backend_error_in_log", return_value=("", "", ""))
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_no_log_file(self, _h: MagicMock, _f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = False
            mock_path.return_value = mock_log
            has_errors, msg = _check_cups_backend_errors("B")
            assert has_errors is False

    @patch(
        f"{MOD}._find_backend_error_in_log", return_value=("error", "2025-01-02", "")
    )
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_has_errors(self, _h: MagicMock, _f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.return_value = "log content"
            mock_path.return_value = mock_log
            has_errors, msg = _check_cups_backend_errors("B")
            assert has_errors is True

    @patch(
        f"{MOD}._find_backend_error_in_log",
        return_value=("error", "2025-01-01", "2025-01-02"),
    )
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_success_after_error(self, _h: MagicMock, _f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.return_value = "log content"
            mock_path.return_value = mock_log
            has_errors, msg = _check_cups_backend_errors("B")
            assert has_errors is False

    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_oserror_reading_log(self, _h: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.side_effect = OSError("fail")
            mock_path.return_value = mock_log
            has_errors, msg = _check_cups_backend_errors("B")
            assert has_errors is False

    @patch(f"{MOD}._find_backend_error_in_log", return_value=("", "", ""))
    @patch(f"{MOD}._is_cups_printer_healthy", return_value=False)
    def test_no_backend_error_in_log(self, _h: MagicMock, _f: MagicMock) -> None:
        with patch(f"{MOD}.Path") as mock_path:
            mock_log = MagicMock()
            mock_log.exists.return_value = True
            mock_log.read_text.return_value = "clean log"
            mock_path.return_value = mock_log
            has_errors, msg = _check_cups_backend_errors("B")
            assert has_errors is False

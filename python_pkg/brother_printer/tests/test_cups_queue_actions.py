"""Tests for brother_printer.cups_queue - the CUPS fix action primitives.

Split from test_cups_queue.py under the 250-line cap. These are the four
functions that shell out to cupsenable, cancel and systemctl, so every one of
them patches shutil.which and subprocess on the module under test.
"""

from __future__ import annotations

from io import StringIO
import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_queue import (
    _cups_cancel_all_jobs,
    _cups_cancel_job,
    _cups_enable_printer,
    _cups_restart_service,
)

MOD = "python_pkg.brother_printer.cups_queue"


class TestCupsEnablePrinter:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_cupsenable(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_enable_printer("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cupsenable")
    def test_success(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _cups_enable_printer("B") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cupsenable")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("cupsenable", 5)
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_enable_printer("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cupsenable")
    def test_oserror(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_enable_printer("B") is False


class TestCupsCancelAllJobs:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_cancel(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_cancel_all_jobs("B") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_success(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _cups_cancel_all_jobs("B") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_error(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "cancel")
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_cancel_all_jobs("B") is False


class TestCupsCancelJob:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_cancel(self, m: MagicMock) -> None:
        assert _cups_cancel_job("job-1") is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_success(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _cups_cancel_job("job-1") is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/cancel")
    def test_error(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "cancel")
        assert _cups_cancel_job("job-1") is False


class TestCupsRestartService:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_systemctl(self, m: MagicMock) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_restart_service() is False

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.time.time")
    @patch(f"{MOD}.subprocess.Popen")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_success(
        self,
        w: MagicMock,
        mock_popen: MagicMock,
        mock_time: MagicMock,
        s: MagicMock,
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
        w: MagicMock,
        mock_popen: MagicMock,
        mock_time: MagicMock,
        s: MagicMock,
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
        w: MagicMock,
        mock_popen: MagicMock,
        mock_time: MagicMock,
        s: MagicMock,
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
    def test_oserror(self, w: MagicMock, mock_popen: MagicMock) -> None:
        mock_popen.side_effect = OSError("fail")
        with patch("sys.stdout", new_callable=StringIO):
            assert _cups_restart_service() is False

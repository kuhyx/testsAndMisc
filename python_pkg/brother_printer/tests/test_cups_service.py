"""Tests for brother_printer.cups_service - pyusb info and service control."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    _ensure_cups_running,
    _get_pyusb_device_info,
    is_cups_scheduler_running,
    start_cups,
)

MOD = "python_pkg.brother_printer.cups_service"


class TestGetPyusbDeviceInfo:
    def test_found(self) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.product = "HL-1110"
        mock_dev.serial_number = "SN123"
        mock_usb.core.find.return_value = mock_dev
        with patch.dict(_sys.modules, {"usb": mock_usb, "usb.core": mock_usb.core}):
            result = _get_pyusb_device_info()
            assert result["product"] == "HL-1110"
            assert result["serial"] == "SN123"

    def test_import_error(self) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_usb.core.find.side_effect = ImportError("no usb")
        with patch.dict(_sys.modules, {"usb": mock_usb, "usb.core": mock_usb.core}):
            result = _get_pyusb_device_info()
            assert result == {}

    def test_not_found(self) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_usb.core.find.return_value = None
        with patch.dict(_sys.modules, {"usb": mock_usb, "usb.core": mock_usb.core}):
            result = _get_pyusb_device_info()
            assert result == {}

    def test_none_product_serial(self) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.product = None
        mock_dev.serial_number = None
        mock_usb.core.find.return_value = mock_dev
        with patch.dict(_sys.modules, {"usb": mock_usb, "usb.core": mock_usb.core}):
            result = _get_pyusb_device_info()
            assert result["product"] == ""
            assert result["serial"] == ""

    def test_oserror(self) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_usb.core.find.side_effect = OSError("usb fail")
        with patch.dict(_sys.modules, {"usb": mock_usb, "usb.core": mock_usb.core}):
            result = _get_pyusb_device_info()
            assert result == {}

    def test_value_error(self) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_usb.core.find.side_effect = ValueError("bad")
        with patch.dict(_sys.modules, {"usb": mock_usb, "usb.core": mock_usb.core}):
            result = _get_pyusb_device_info()
            assert result == {}


class TestIsCupsSchedulerRunning:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, m: MagicMock) -> None:
        assert is_cups_scheduler_running() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_running(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="scheduler is running")
        assert is_cups_scheduler_running() is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_not_running(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="scheduler is not running")
        assert is_cups_scheduler_running() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 3)
        assert is_cups_scheduler_running() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_oserror(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert is_cups_scheduler_running() is False


class TestStartCups:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_systemctl(self, m: MagicMock) -> None:
        assert start_cups() is False

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.is_cups_scheduler_running")
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_success(
        self,
        w: MagicMock,
        mock_run: MagicMock,
        mock_is_running: MagicMock,
        s: MagicMock,
    ) -> None:
        mock_run.return_value = MagicMock()
        mock_is_running.return_value = True
        assert start_cups() is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("systemctl", 15)
        assert start_cups() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_called_process_error(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "systemctl")
        assert start_cups() is False

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=False)
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_never_starts(
        self,
        w: MagicMock,
        mock_run: MagicMock,
        is_running: MagicMock,
        s: MagicMock,
    ) -> None:
        mock_run.return_value = MagicMock()
        assert start_cups() is False


class TestEnsureCupsRunning:
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=True)
    def test_already_running(self, m: MagicMock) -> None:
        assert _ensure_cups_running() is True

    @patch(f"{MOD}.start_cups", return_value=True)
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=False)
    def test_needs_start(self, is_running: MagicMock, st: MagicMock) -> None:
        assert _ensure_cups_running() is True

    @patch(f"{MOD}.start_cups", return_value=False)
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=False)
    def test_start_fails(self, is_running: MagicMock, st: MagicMock) -> None:
        assert _ensure_cups_running() is False

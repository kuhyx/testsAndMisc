"""Tests for brother_printer.cups_service module."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    _ensure_cups_running,
    _get_cups_total_pages,
    _get_pyusb_device_info,
    _load_consumable_state,
    _query_usb_port_status_raw,
    _save_consumable_state,
    _stop_cups,
    is_cups_scheduler_running,
    reset_consumable,
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


class TestStopCups:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_systemctl(self, _m: MagicMock) -> None:
        assert _stop_cups() is False

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_success(self, _w: MagicMock, mock_run: MagicMock, _s: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        assert _stop_cups() is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("systemctl", 15)
        assert _stop_cups() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_called_process_error(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "systemctl")
        assert _stop_cups() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert _stop_cups() is False


class TestIsCupsSchedulerRunning:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, _m: MagicMock) -> None:
        assert is_cups_scheduler_running() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_running(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="scheduler is running")
        assert is_cups_scheduler_running() is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_not_running(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="scheduler is not running")
        assert is_cups_scheduler_running() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 3)
        assert is_cups_scheduler_running() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert is_cups_scheduler_running() is False


class TestStartCups:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_systemctl(self, _m: MagicMock) -> None:
        assert start_cups() is False

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.is_cups_scheduler_running")
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_success(
        self,
        _w: MagicMock,
        mock_run: MagicMock,
        mock_is_running: MagicMock,
        _s: MagicMock,
    ) -> None:
        mock_run.return_value = MagicMock()
        mock_is_running.return_value = True
        assert start_cups() is True

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("systemctl", 15)
        assert start_cups() is False

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_called_process_error(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "systemctl")
        assert start_cups() is False

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=False)
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/systemctl")
    def test_never_starts(
        self,
        _w: MagicMock,
        mock_run: MagicMock,
        _is: MagicMock,
        _s: MagicMock,
    ) -> None:
        mock_run.return_value = MagicMock()
        assert start_cups() is False


class TestEnsureCupsRunning:
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=True)
    def test_already_running(self, _m: MagicMock) -> None:
        assert _ensure_cups_running() is True

    @patch(f"{MOD}.start_cups", return_value=True)
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=False)
    def test_needs_start(self, _is: MagicMock, _st: MagicMock) -> None:
        assert _ensure_cups_running() is True

    @patch(f"{MOD}.start_cups", return_value=False)
    @patch(f"{MOD}.is_cups_scheduler_running", return_value=False)
    def test_start_fails(self, _is: MagicMock, _st: MagicMock) -> None:
        assert _ensure_cups_running() is False


class TestQueryUsbPortStatusRaw:
    def test_import_error(self) -> None:
        with patch(f"{MOD}._stop_cups"):
            # Simulate ImportError for usb.core
            with patch.dict(
                "sys.modules", {"usb": None, "usb.core": None, "usb.util": None}
            ):
                result = _query_usb_port_status_raw()
                assert result is None

    @patch(f"{MOD}.start_cups")
    @patch(f"{MOD}._stop_cups", return_value=False)
    def test_stop_cups_fails(self, _st: MagicMock, _s: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_usb.core.find.return_value = MagicMock()
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            result = _query_usb_port_status_raw()
            assert result is None

    @patch(f"{MOD}.start_cups")
    @patch(f"{MOD}._stop_cups", return_value=True)
    def test_dev_none_after_reset(self, _st: MagicMock, _s: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_usb.core.find.side_effect = [mock_dev, None]
        with (
            patch.dict(
                _sys.modules,
                {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
            ),
            patch(f"{MOD}.time.sleep"),
        ):
            result = _query_usb_port_status_raw()
            assert result is None

    @patch(f"{MOD}.start_cups")
    @patch(f"{MOD}._stop_cups", return_value=True)
    def test_success(self, _stop: MagicMock, _start: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = True
        mock_dev.ctrl_transfer.return_value = [0x18]
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = type("USBError", (Exception,), {})
        with (
            patch.dict(
                _sys.modules,
                {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
            ),
            patch(f"{MOD}.time.sleep"),
        ):
            result = _query_usb_port_status_raw()
            assert result is not None
            assert result.online is True

    @patch(f"{MOD}.start_cups")
    @patch(f"{MOD}._stop_cups", return_value=True)
    def test_kernel_driver_not_active(
        self, _stop: MagicMock, _start: MagicMock
    ) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = False
        mock_dev.ctrl_transfer.return_value = [0x18]
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = type("USBError", (Exception,), {})
        with (
            patch.dict(
                _sys.modules,
                {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
            ),
            patch(f"{MOD}.time.sleep"),
        ):
            result = _query_usb_port_status_raw()
            assert result is not None

    @patch(f"{MOD}.start_cups")
    @patch(f"{MOD}._stop_cups", return_value=True)
    def test_kernel_driver_usberror(self, _stop: MagicMock, _start: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        usb_error_cls = type("USBError", (Exception,), {})
        mock_dev.is_kernel_driver_active.side_effect = usb_error_cls("err")
        mock_dev.ctrl_transfer.return_value = [0x18]
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = usb_error_cls
        with (
            patch.dict(
                _sys.modules,
                {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
            ),
            patch(f"{MOD}.time.sleep"),
        ):
            result = _query_usb_port_status_raw()
            assert result is not None

    @patch(f"{MOD}.start_cups")
    @patch(f"{MOD}._stop_cups", return_value=True)
    def test_oserror_during_transfer(self, _stop: MagicMock, _start: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = False
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = type("USBError", (Exception,), {})
        mock_usb.util.claim_interface.side_effect = OSError("usb fail")
        with (
            patch.dict(
                _sys.modules,
                {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
            ),
            patch(f"{MOD}.time.sleep"),
        ):
            result = _query_usb_port_status_raw()
            assert result is None

    @patch(f"{MOD}.start_cups")
    @patch(f"{MOD}._stop_cups", return_value=True)
    def test_dev_none_initial(self, _stop: MagicMock, _start: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_usb.core.find.return_value = None
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            result = _query_usb_port_status_raw()
            assert result is None


class TestGetCupsTotalPages:
    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_no_log(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = False
        assert _get_cups_total_pages() == 0

    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_with_entries(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = True
        mock_log.read_text.return_value = (
            "printer 1 [2025-01-01] total 5\n"
            "printer 2 [2025-01-01] total 3\n"
            "printer 1 [2025-01-01] total 10\n"
        )
        assert _get_cups_total_pages() == 13  # max(5,10) + 3

    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_oserror(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = True
        mock_log.read_text.side_effect = OSError("fail")
        assert _get_cups_total_pages() == 0

    @patch(f"{MOD}.CUPS_PAGE_LOG")
    def test_no_matching_lines(self, mock_log: MagicMock) -> None:
        mock_log.exists.return_value = True
        mock_log.read_text.return_value = "some garbage\n"
        assert _get_cups_total_pages() == 0


class TestLoadConsumableState:
    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_no_file(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = False
        result = _load_consumable_state()
        assert result == {"toner_replaced_at": 0, "drum_replaced_at": 0}

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_valid_file(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps(
            {"toner_replaced_at": 100, "drum_replaced_at": 200},
        )
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 100
        assert result["drum_replaced_at"] == 200

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_oserror(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.side_effect = OSError("fail")
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 0

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_bad_json(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "not json"
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 0

    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_bad_values(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps(
            {"toner_replaced_at": "bad"},
        )
        result = _load_consumable_state()
        assert result["toner_replaced_at"] == 0


class TestSaveConsumableState:
    @patch(f"{MOD}.CONSUMABLE_STATE_FILE")
    def test_saves(self, mock_file: MagicMock) -> None:
        mock_file.parent = MagicMock()
        _save_consumable_state({"toner_replaced_at": 100, "drum_replaced_at": 200})
        mock_file.write_text.assert_called_once()
        written = mock_file.write_text.call_args[0][0]
        data = json.loads(written)
        assert data["toner_replaced_at"] == 100


class TestResetConsumable:
    @patch(f"{MOD}._out")
    @patch(f"{MOD}._save_consumable_state")
    @patch(f"{MOD}._load_consumable_state")
    @patch(f"{MOD}._get_cups_total_pages", return_value=500)
    def test_reset_toner(
        self,
        _pages: MagicMock,
        _load: MagicMock,
        mock_save: MagicMock,
        _out: MagicMock,
    ) -> None:
        _load.return_value = {"toner_replaced_at": 0, "drum_replaced_at": 0}
        reset_consumable("toner")
        saved_state = mock_save.call_args[0][0]
        assert saved_state["toner_replaced_at"] == 500

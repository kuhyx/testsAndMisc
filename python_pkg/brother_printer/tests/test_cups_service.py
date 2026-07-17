"""Tests for brother_printer.cups_service module."""

from __future__ import annotations

import json
import os
import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    STATE_SCHEMA_CUPS_SCALE,
    _cups_is_busy,
    _ensure_cups_running,
    _get_cups_total_pages,
    _get_pyusb_device_info,
    _load_consumable_state,
    _port_status_via_usblp,
    _query_usb_port_status_raw,
    _save_consumable_state,
    is_cups_scheduler_running,
    reset_consumable,
    start_cups,
)
from python_pkg.brother_printer.data_classes import USBPortStatus

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


class TestPortStatusViaUsblp:
    """The zero-side-effect path: read the status byte from /dev/usb/lp*."""

    @patch(f"{MOD}.Path")
    def test_no_dev_dir(self, mock_path: MagicMock) -> None:
        mock_path.return_value.is_dir.return_value = False
        assert _port_status_via_usblp() is None

    @patch(f"{MOD}.Path")
    def test_no_devices(self, mock_path: MagicMock) -> None:
        mock_path.return_value.is_dir.return_value = True
        mock_path.return_value.glob.return_value = []
        assert _port_status_via_usblp() is None

    @patch(f"{MOD}.os.close")
    @patch(f"{MOD}.fcntl.ioctl")
    @patch(f"{MOD}.os.open", return_value=7)
    @patch(f"{MOD}.Path")
    def test_success(
        self,
        mock_path: MagicMock,
        mock_open: MagicMock,
        mock_ioctl: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        mock_path.return_value.is_dir.return_value = True
        mock_path.return_value.glob.return_value = ["/dev/usb/lp0"]

        def fill(fd: int, req: int, buf: bytearray) -> None:
            buf[0] = 0x18

        mock_ioctl.side_effect = fill
        result = _port_status_via_usblp()
        assert result is not None
        assert result.online is True
        assert result.error is False
        assert result.paper_empty is False
        # Must never block: the printer may be mid-job.
        assert mock_open.call_args[0][1] & os.O_NONBLOCK
        mock_close.assert_called_once_with(7)

    @patch(f"{MOD}.os.open", side_effect=OSError("busy"))
    @patch(f"{MOD}.Path")
    def test_open_fails(self, mock_path: MagicMock, mock_open: MagicMock) -> None:
        mock_path.return_value.is_dir.return_value = True
        mock_path.return_value.glob.return_value = ["/dev/usb/lp0"]
        assert _port_status_via_usblp() is None


class TestQueryUsbPortStatusRaw:
    @patch(f"{MOD}._port_status_via_usblp", return_value=USBPortStatus(raw_byte=0x18))
    def test_prefers_usblp(self, m: MagicMock) -> None:
        """The free path wins; pyusb is never touched."""
        result = _query_usb_port_status_raw("idle")
        assert result is not None
        assert result.raw_byte == 0x18

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_never_probes_while_printing(self, m: MagicMock) -> None:
        """Regression: probing mid-job used to stop CUPS and kill the print."""
        import sys as _sys

        mock_usb = MagicMock()
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            assert _query_usb_port_status_raw("processing") is None
        mock_usb.core.find.assert_not_called()

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_import_error(self, m: MagicMock) -> None:
        with patch.dict(
            "sys.modules", {"usb": None, "usb.core": None, "usb.util": None}
        ):
            assert _query_usb_port_status_raw("idle") is None

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_dev_none(self, m: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_usb.core.find.return_value = None
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            assert _query_usb_port_status_raw("idle") is None

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_success_reattaches_driver(self, m: MagicMock) -> None:
        """usblp must get its device back, or every later run hits the fallback."""
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = True
        mock_dev.ctrl_transfer.return_value = [0x18]
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = type("USBError", (Exception,), {})
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            result = _query_usb_port_status_raw("idle")
        assert result is not None
        assert result.online is True
        mock_dev.reset.assert_not_called()
        mock_dev.attach_kernel_driver.assert_called_once_with(0)

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_kernel_driver_not_active(self, m: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = False
        mock_dev.ctrl_transfer.return_value = [0x18]
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = type("USBError", (Exception,), {})
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            result = _query_usb_port_status_raw("idle")
        assert result is not None
        # Nothing was detached, so nothing should be re-attached.
        mock_dev.attach_kernel_driver.assert_not_called()

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_kernel_driver_usberror(self, m: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        usb_error_cls = type("USBError", (Exception,), {})
        mock_dev.is_kernel_driver_active.side_effect = usb_error_cls("err")
        mock_dev.ctrl_transfer.return_value = [0x18]
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = usb_error_cls
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            assert _query_usb_port_status_raw("idle") is not None

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_oserror_during_transfer(self, m: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = False
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = type("USBError", (Exception,), {})
        mock_usb.util.claim_interface.side_effect = OSError("usb fail")
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            assert _query_usb_port_status_raw("idle") is None

    @patch(f"{MOD}._port_status_via_usblp", return_value=None)
    def test_attach_failure_is_survivable(self, m: MagicMock) -> None:
        import sys as _sys

        mock_usb = MagicMock()
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = True
        mock_dev.ctrl_transfer.return_value = [0x18]
        mock_dev.attach_kernel_driver.side_effect = OSError("cannot reattach")
        mock_usb.core.find.return_value = mock_dev
        mock_usb.core.USBError = type("USBError", (Exception,), {})
        with patch.dict(
            _sys.modules,
            {"usb": mock_usb, "usb.core": mock_usb.core, "usb.util": mock_usb.util},
        ):
            assert _query_usb_port_status_raw("idle") is not None


class TestCupsIsBusy:
    def test_processing(self) -> None:
        assert _cups_is_busy("processing") is True

    def test_printing_text(self) -> None:
        assert _cups_is_busy("now printing Brother-98") is True

    def test_idle(self) -> None:
        assert _cups_is_busy("idle") is False

    def test_empty(self) -> None:
        assert _cups_is_busy("") is False


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
        assert result == {
            "toner_replaced_at": 0,
            "drum_replaced_at": 0,
            "schema": STATE_SCHEMA_CUPS_SCALE,
            "last_printer_count": 0,
            "last_cups_total": 0,
        }

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
        pages: MagicMock,
        load: MagicMock,
        mock_save: MagicMock,
        out: MagicMock,
    ) -> None:
        load.return_value = {"toner_replaced_at": 0, "drum_replaced_at": 0}
        reset_consumable("toner")
        saved_state = mock_save.call_args[0][0]
        assert saved_state["toner_replaced_at"] == 500


class TestPortStatusViaUsblpIoctlFailure:
    @patch(f"{MOD}.os.close")
    @patch(f"{MOD}.fcntl.ioctl", side_effect=OSError("not supported"))
    @patch(f"{MOD}.os.open", return_value=7)
    @patch(f"{MOD}.Path")
    def test_ioctl_failure_still_closes_fd(
        self,
        mock_path: MagicMock,
        mock_open: MagicMock,
        mock_ioctl: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        """A failed ioctl must not leak the fd, or usblp stays busy."""
        mock_path.return_value.is_dir.return_value = True
        mock_path.return_value.glob.return_value = ["/dev/usb/lp0"]
        assert _port_status_via_usblp() is None
        mock_close.assert_called_once_with(7)

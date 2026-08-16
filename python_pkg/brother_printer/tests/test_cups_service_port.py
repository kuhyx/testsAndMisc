"""Tests for brother_printer.cups_service - USB port status via usblp.

Split from test_cups_service.py under the 250-line cap. These tests read the
printer's IEEE 1284 status byte through an ioctl on /dev/usb/lp*, so they patch
fcntl, os and Path on the module under test.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    _cups_is_busy,
    _port_status_via_usblp,
    _query_usb_port_status_raw,
)
from python_pkg.brother_printer.data_classes import USBPortStatus

MOD = "python_pkg.brother_printer.cups_service"


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

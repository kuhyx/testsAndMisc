"""Tests for brother_printer.usb_query module."""

from __future__ import annotations

import errno
import os
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.data_classes import USBResult
from python_pkg.brother_printer.usb_query import (
    _init_usb_result,
    _parse_pagecount,
    _parse_status,
    _parse_variables,
    _retry_pjl_query,
    _run_pjl_queries,
    find_brother_usb,
    find_usb_printer_dev,
    query_usb_pjl,
)

MOD = "python_pkg.brother_printer.usb_query"


class TestFindBrotherUsb:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lsusb(self, m: MagicMock) -> None:
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_found(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="Bus 001 Device 005: ID 04f9:0042 Brother Industries\n",
        )
        result = find_brother_usb()
        assert "Brother" in result

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_not_found(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="Bus 001 Device 001: Hub\n")
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_line_with_colon_sep(self, w: MagicMock, mock_run: MagicMock) -> None:
        """Line contains 04f9: but no ': ' separator → returns full line."""
        mock_run.return_value = MagicMock(stdout="ID 04f9:0042\n")
        result = find_brother_usb()
        assert result == "ID 04f9:0042"

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_no_match(self, w: MagicMock, mock_run: MagicMock) -> None:
        """Line without 04f9: vendor id is ignored."""
        mock_run.return_value = MagicMock(stdout="04f9 brother no colon\n")
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("lsusb", 5)
        assert find_brother_usb() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_oserror(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert find_brother_usb() == ""


class TestFindUsbPrinterDev:
    @patch(f"{MOD}.Path")
    def test_found(self, mock_path_cls: MagicMock) -> None:
        mock_path_cls.return_value = mock_path_cls
        mock_path_cls.__truediv__ = lambda _self, _x: mock_path_cls
        lp0 = MagicMock()
        lp0.__str__ = lambda _s: "/dev/usb/lp0"
        lp0.__lt__ = lambda s, o: str(s) < str(o)
        mock_usb = MagicMock()
        mock_usb.glob.return_value = [lp0]
        mock_path_cls.side_effect = None
        with patch(f"{MOD}.Path", return_value=mock_usb):
            result = find_usb_printer_dev()
            assert result == "/dev/usb/lp0"

    @patch(f"{MOD}.Path")
    def test_not_found(self, mock_path_cls: MagicMock) -> None:
        mock_usb = MagicMock()
        mock_usb.glob.return_value = []
        mock_path_cls.return_value = mock_usb
        result = find_usb_printer_dev()
        assert result is None


class TestParseStatus:
    def test_found(self) -> None:
        result = USBResult()
        resp = 'CODE=10001\nDISPLAY= "Ready" \nONLINE=TRUE\n'
        assert _parse_status(resp, result) is True
        assert result.status_code == "10001"
        assert result.display == "Ready"
        assert result.online == "TRUE"

    def test_not_found(self) -> None:
        result = USBResult()
        assert _parse_status("nothing here\n", result) is False

    def test_partial(self) -> None:
        result = USBResult()
        resp = "DISPLAY=Hello\n"
        assert _parse_status(resp, result) is False
        assert result.display == "Hello"


class TestParseVariables:
    def test_found(self) -> None:
        result = USBResult()
        resp = "ECONOMODE=ON extra\n"
        assert _parse_variables(resp, result) is True
        assert result.economode == "ON"

    def test_not_found(self) -> None:
        result = USBResult()
        assert _parse_variables("nothing\n", result) is False


class TestRetryPjlQuery:
    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}._drain_buffer")
    @patch(f"{MOD}.pjl_query")
    def test_success_first_attempt(
        self,
        mock_pjl: MagicMock,
        d: MagicMock,
        s: MagicMock,
    ) -> None:
        result = USBResult()
        mock_pjl.return_value = "CODE=10001\n"
        _retry_pjl_query(42, "@PJL INFO STATUS", _parse_status, result, 2)
        assert result.status_code == "10001"
        assert mock_pjl.call_count == 1

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}._drain_buffer")
    @patch(f"{MOD}.pjl_query")
    def test_retry_then_success(
        self,
        mock_pjl: MagicMock,
        d: MagicMock,
        s: MagicMock,
    ) -> None:
        result = USBResult()
        mock_pjl.side_effect = ["garbage\n", "CODE=10001\n"]
        _retry_pjl_query(42, "@PJL INFO STATUS", _parse_status, result, 2)
        assert result.status_code == "10001"
        assert mock_pjl.call_count == 2

    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}._drain_buffer")
    @patch(f"{MOD}.pjl_query")
    def test_all_retries_fail(
        self,
        mock_pjl: MagicMock,
        d: MagicMock,
        s: MagicMock,
    ) -> None:
        result = USBResult()
        mock_pjl.return_value = "garbage\n"
        _retry_pjl_query(42, "@PJL INFO STATUS", _parse_status, result, 2)
        assert result.status_code == ""
        assert mock_pjl.call_count == 3


class TestRunPjlQueries:
    @patch(f"{MOD}._retry_pjl_query")
    @patch(f"{MOD}.time.sleep")
    @patch(f"{MOD}._drain_buffer")
    @patch(f"{MOD}._write_with_deadline")
    def test_runs_status_pagecount_and_variables(
        self,
        mock_write: MagicMock,
        d: MagicMock,
        s: MagicMock,
        mock_retry: MagicMock,
    ) -> None:
        result = USBResult()
        _run_pjl_queries(42, result, 2)
        assert mock_retry.call_count == 3
        queried = [call.args[1] for call in mock_retry.call_args_list]
        assert "@PJL INFO PAGECOUNT" in queried


class TestParsePagecount:
    def test_found(self) -> None:
        result = USBResult()
        assert _parse_pagecount("PAGECOUNT=2014\n", result) is True
        assert result.page_count == "2014"

    def test_not_found(self) -> None:
        result = USBResult()
        assert _parse_pagecount("nothing\n", result) is False
        assert result.page_count == ""

    def test_non_numeric_rejected(self) -> None:
        """A garbled reply must not become a page count."""
        result = USBResult()
        assert _parse_pagecount("PAGECOUNT=???\n", result) is False
        assert result.page_count == ""


class TestInitUsbResult:
    @patch(f"{MOD}.printer_info_from_cups")
    def test_from_cups(self, mock_cups: MagicMock) -> None:
        mock_cups.return_value = {"product": "HL-1110", "serial": "SN1"}
        result = _init_usb_result("/dev/usb/lp0")
        assert result.device == "/dev/usb/lp0"
        assert result.product == "HL-1110"
        assert result.serial == "SN1"

    @patch(f"{MOD}.printer_info_from_cups")
    def test_no_product(self, mock_cups: MagicMock) -> None:
        mock_cups.return_value = {"product": "", "serial": ""}
        result = _init_usb_result("/dev/usb/lp0")
        assert result.product == "Brother Laser Printer"


class TestQueryUsbPjl:
    def test_success(self) -> None:
        with (
            patch(f"{MOD}.find_usb_printer_dev", return_value="/dev/usb/lp0"),
            patch(f"{MOD}._init_usb_result") as mock_init,
            patch(f"{MOD}.os.access", return_value=True),
            patch(f"{MOD}.os.open", return_value=10) as mock_open,
            patch(f"{MOD}._run_pjl_queries"),
            patch(f"{MOD}.os.close"),
        ):
            mock_init.return_value = USBResult(
                device="/dev/usb/lp0",
                status_code="10001",
            )
            result = query_usb_pjl()
            assert result.device == "/dev/usb/lp0"
            assert result.error == ""
        # The whole point: a blocking open() hangs on an unwell printer.
        assert mock_open.call_args[0][1] & os.O_NONBLOCK

    @patch(f"{MOD}.find_usb_printer_dev", return_value=None)
    def test_no_dev_falls_back_to_cups(self, f: MagicMock) -> None:
        with patch(
            "python_pkg.brother_printer.cups_service.query_usb_via_cups",
        ) as mock_cups:
            mock_cups.return_value = USBResult(device="cups")
            result = query_usb_pjl()
            assert result.device == "cups"

    @patch(f"{MOD}.os.access", return_value=False)
    @patch(f"{MOD}._init_usb_result")
    @patch(f"{MOD}.find_usb_printer_dev", return_value="/dev/usb/lp0")
    def test_permission_denied(
        self,
        f: MagicMock,
        mock_init: MagicMock,
        a: MagicMock,
    ) -> None:
        mock_init.return_value = USBResult(device="/dev/usb/lp0")
        result = query_usb_pjl()
        assert "Permission denied" in result.error

    def test_silent_printer_is_reported_not_hidden(self) -> None:
        """A printer that answers nothing must say so, not look healthy."""
        with (
            patch(f"{MOD}.find_usb_printer_dev", return_value="/dev/usb/lp0"),
            patch(f"{MOD}._init_usb_result") as mock_init,
            patch(f"{MOD}.os.access", return_value=True),
            patch(f"{MOD}.os.open", return_value=10),
            patch(f"{MOD}._run_pjl_queries"),
            patch(f"{MOD}.os.close"),
        ):
            mock_init.return_value = USBResult(device="/dev/usb/lp0")
            result = query_usb_pjl()
        assert "did not answer" in result.error

    def test_busy_device_explains_why(self) -> None:
        """EBUSY means CUPS holds the printer mid-job; say that."""
        exc = OSError("busy")
        exc.errno = errno.EBUSY
        with (
            patch(f"{MOD}.find_usb_printer_dev", return_value="/dev/usb/lp0"),
            patch(f"{MOD}._init_usb_result") as mock_init,
            patch(f"{MOD}.os.access", return_value=True),
            patch(f"{MOD}.os.open", side_effect=exc),
        ):
            mock_init.return_value = USBResult(device="/dev/usb/lp0")
            result = query_usb_pjl()
        assert "busy" in result.error.lower()

    def test_eacces_suggests_sudo(self) -> None:
        exc = OSError("denied")
        exc.errno = errno.EACCES
        with (
            patch(f"{MOD}.find_usb_printer_dev", return_value="/dev/usb/lp0"),
            patch(f"{MOD}._init_usb_result") as mock_init,
            patch(f"{MOD}.os.access", return_value=True),
            patch(f"{MOD}.os.open", side_effect=exc),
        ):
            mock_init.return_value = USBResult(device="/dev/usb/lp0")
            result = query_usb_pjl()
        assert "sudo" in result.error

    @patch(f"{MOD}.os.open", side_effect=OSError("no device"))
    @patch(f"{MOD}.os.access", return_value=True)
    @patch(f"{MOD}._init_usb_result")
    @patch(f"{MOD}.find_usb_printer_dev", return_value="/dev/usb/lp0")
    def test_oserror_fd_none(
        self,
        f: MagicMock,
        mock_init: MagicMock,
        a: MagicMock,
        o: MagicMock,
    ) -> None:
        """os.open raises OSError before fd is set -> fd stays None."""
        mock_init.return_value = USBResult(device="/dev/usb/lp0")
        result = query_usb_pjl()
        assert "no device" in result.error

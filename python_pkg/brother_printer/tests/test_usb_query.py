"""Tests for brother_printer.usb_query module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.data_classes import USBResult
from python_pkg.brother_printer.usb_query import (
    _drain_buffer,
    _init_usb_result,
    _parse_cups_usb_uri,
    _parse_status,
    _parse_variables,
    _read_nonblocking,
    _retry_pjl_query,
    _run_pjl_queries,
    _wait_for_pjl_response,
    find_brother_usb,
    find_usb_printer_dev,
    get_printer_info_from_cups,
    pjl_query,
    query_usb_pjl,
)

MOD = "python_pkg.brother_printer.usb_query"


class TestFindBrotherUsb:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lsusb(self, m: MagicMock) -> None:
        assert find_brother_usb() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_found(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="Bus 001 Device 005: ID 04f9:0042 Brother Industries\n",
        )
        result = find_brother_usb()
        assert "Brother" in result

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_not_found(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="Bus 001 Device 001: Hub\n")
        assert find_brother_usb() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_line_with_colon_sep(self, w: MagicMock, mock_run: MagicMock) -> None:
        """Line contains 04f9: but no ': ' separator → returns full line."""
        mock_run.return_value = MagicMock(stdout="ID 04f9:0042\n")
        result = find_brother_usb()
        assert result == "ID 04f9:0042"

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_no_match(self, w: MagicMock, mock_run: MagicMock) -> None:
        """Line without 04f9: vendor id is ignored."""
        mock_run.return_value = MagicMock(stdout="04f9 brother no colon\n")
        assert find_brother_usb() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lsusb")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("lsusb", 5)
        assert find_brother_usb() == ""

    @patch(f"{MOD}.subprocess.run")
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


class TestParseCupsUsbUri:
    def test_basic_uri(self) -> None:
        info: dict[str, str] = {"product": "", "serial": ""}
        _parse_cups_usb_uri(
            "usb://Brother/HL-1110%20series?serial=ABC123",
            info,
        )
        assert info["product"] == "HL-1110 series"
        assert info["serial"] == "ABC123"

    def test_no_serial(self) -> None:
        info: dict[str, str] = {"product": "", "serial": ""}
        _parse_cups_usb_uri("usb://Brother/HL-1110%20series", info)
        assert info["product"] == "HL-1110 series"
        assert info["serial"] == ""


class TestGetPrinterInfoFromCups:
    @patch(f"{MOD}.subprocess.run")
    def test_found(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for Brother: usb://Brother/HL-1110?serial=SN1\n",
        )
        info = get_printer_info_from_cups()
        assert info["product"] == "HL-1110"
        assert info["serial"] == "SN1"

    @patch(f"{MOD}.subprocess.run")
    def test_no_brother(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="device for HP: ipp://hp\n")
        info = get_printer_info_from_cups()
        assert info["product"] == ""

    @patch(f"{MOD}.subprocess.run")
    def test_brother_no_usb_uri(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for Brother: ipp://1.2.3.4\n",
        )
        info = get_printer_info_from_cups()
        assert info["product"] == ""

    @patch(f"{MOD}.subprocess.run")
    def test_timeout(self, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        info = get_printer_info_from_cups()
        assert info == {"product": "", "serial": ""}

    @patch(f"{MOD}.subprocess.run")
    def test_oserror(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        info = get_printer_info_from_cups()
        assert info == {"product": "", "serial": ""}


class TestDrainBuffer:
    @patch(f"{MOD}.os.read")
    @patch(f"{MOD}.fcntl.fcntl")
    def test_drain(self, mock_fcntl: MagicMock, mock_read: MagicMock) -> None:
        mock_fcntl.return_value = 0
        mock_read.side_effect = [b"data", OSError("done")]
        _drain_buffer(42)
        assert mock_read.called

    @patch(f"{MOD}.os.read")
    @patch(f"{MOD}.fcntl.fcntl")
    def test_drain_empty_buffer(
        self,
        mock_fcntl: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        """Buffer is already empty — os.read returns b'' immediately."""
        mock_fcntl.return_value = 0
        mock_read.return_value = b""
        _drain_buffer(42)
        mock_read.assert_called_once()


class TestReadNonblocking:
    @patch(f"{MOD}.os.read")
    @patch(f"{MOD}.fcntl.fcntl")
    def test_reads_chunks(self, mock_fcntl: MagicMock, mock_read: MagicMock) -> None:
        mock_fcntl.return_value = 0
        mock_read.side_effect = [b"hello", b"", OSError]
        result = _read_nonblocking(42, 0)
        assert result == b"hello"

    @patch(f"{MOD}.os.read")
    @patch(f"{MOD}.fcntl.fcntl")
    def test_oserror_suppressed(
        self,
        mock_fcntl: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        mock_fcntl.return_value = 0
        mock_read.side_effect = OSError("would block")
        result = _read_nonblocking(42, 0)
        assert result == b""


class TestWaitForPjlResponse:
    @patch(f"{MOD}._read_nonblocking")
    @patch(f"{MOD}.select.select")
    @patch(f"{MOD}.time.time")
    def test_response_with_equals(
        self,
        mock_time: MagicMock,
        mock_select: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        mock_time.side_effect = [0.0, 0.5, 1.0]
        mock_select.return_value = ([42], [], [])
        mock_read.return_value = b"CODE=10001"
        result = _wait_for_pjl_response(42, 0, 5.0)
        assert b"CODE=10001" in result

    @patch(f"{MOD}._read_nonblocking")
    @patch(f"{MOD}.select.select")
    @patch(f"{MOD}.time.time")
    def test_response_with_pjl(
        self,
        mock_time: MagicMock,
        mock_select: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        mock_time.side_effect = [0.0, 0.5, 1.0]
        mock_select.return_value = ([42], [], [])
        mock_read.return_value = b"@PJL INFO"
        result = _wait_for_pjl_response(42, 0, 5.0)
        assert b"@PJL" in result

    @patch(f"{MOD}.select.select")
    @patch(f"{MOD}.time.time")
    def test_timeout_no_data(
        self,
        mock_time: MagicMock,
        mock_select: MagicMock,
    ) -> None:
        mock_time.side_effect = [10.0, 11.0]
        result = _wait_for_pjl_response(42, 0, 5.0)
        assert result == b""

    @patch(f"{MOD}._read_nonblocking")
    @patch(f"{MOD}.select.select")
    @patch(f"{MOD}.time.time")
    def test_not_readable_then_timeout(
        self,
        mock_time: MagicMock,
        mock_select: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        mock_time.side_effect = [0.0, 0.5, 6.0]
        mock_select.return_value = ([], [], [])
        result = _wait_for_pjl_response(42, 0, 5.0)
        assert result == b""

    @patch(f"{MOD}._read_nonblocking")
    @patch(f"{MOD}.select.select")
    @patch(f"{MOD}.time.time")
    def test_remaining_lte_zero(
        self,
        mock_time: MagicMock,
        mock_select: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        """Inner remaining check triggers break."""
        mock_time.side_effect = [0.0, 6.0, 6.0]
        result = _wait_for_pjl_response(42, 0, 5.0)
        assert result == b""
        mock_select.assert_not_called()

    @patch(f"{MOD}._read_nonblocking")
    @patch(f"{MOD}.select.select")
    @patch(f"{MOD}.time.time")
    def test_response_no_eq_or_pjl(
        self,
        mock_time: MagicMock,
        mock_select: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        """Data read but no '=' or '@PJL' → continues loop then times out."""
        mock_time.side_effect = [0.0, 0.5, 1.0, 6.0]
        mock_select.return_value = ([42], [], [])
        mock_read.return_value = b"garbage"
        result = _wait_for_pjl_response(42, 0, 5.0)
        assert result == b"garbage"


class TestPjlQuery:
    @patch(f"{MOD}._wait_for_pjl_response")
    @patch(f"{MOD}.os.write")
    @patch(f"{MOD}.fcntl.fcntl")
    @patch(f"{MOD}.time.time", return_value=100.0)
    def test_query(
        self,
        t: MagicMock,
        mock_fcntl: MagicMock,
        mock_write: MagicMock,
        mock_wait: MagicMock,
    ) -> None:
        mock_fcntl.return_value = 0
        mock_wait.return_value = b"CODE=10001"
        result = pjl_query(42, "@PJL INFO STATUS")
        assert "CODE=10001" in result


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
    @patch(f"{MOD}.os.write")
    def test_runs_both_queries(
        self,
        mock_write: MagicMock,
        d: MagicMock,
        s: MagicMock,
        mock_retry: MagicMock,
    ) -> None:
        result = USBResult()
        _run_pjl_queries(42, result, 2)
        assert mock_retry.call_count == 2


class TestInitUsbResult:
    @patch(f"{MOD}.get_printer_info_from_cups")
    def test_from_cups(self, mock_cups: MagicMock) -> None:
        mock_cups.return_value = {"product": "HL-1110", "serial": "SN1"}
        result = _init_usb_result("/dev/usb/lp0")
        assert result.device == "/dev/usb/lp0"
        assert result.product == "HL-1110"
        assert result.serial == "SN1"

    @patch(f"{MOD}.get_printer_info_from_cups")
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
            patch(f"{MOD}.os.open", return_value=10),
            patch(f"{MOD}.fcntl.fcntl", return_value=0),
            patch(f"{MOD}._run_pjl_queries"),
            patch(f"{MOD}.os.close"),
        ):
            mock_init.return_value = USBResult(device="/dev/usb/lp0")
            result = query_usb_pjl()
            assert result.device == "/dev/usb/lp0"

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

    def test_oserror_on_open(self) -> None:
        with (
            patch(f"{MOD}.find_usb_printer_dev", return_value="/dev/usb/lp0"),
            patch(f"{MOD}._init_usb_result") as mock_init,
            patch(f"{MOD}.os.access", return_value=True),
            patch(f"{MOD}.os.open", return_value=10),
            patch(f"{MOD}.fcntl.fcntl", side_effect=OSError("bad fd")),
            patch(f"{MOD}.os.close"),
        ):
            mock_init.return_value = USBResult(device="/dev/usb/lp0")
            result = query_usb_pjl()
            assert result.error != ""

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
        """os.open raises OSError before fd is set → fd stays None."""
        mock_init.return_value = USBResult(device="/dev/usb/lp0")
        result = query_usb_pjl()
        assert result.error == "no device"

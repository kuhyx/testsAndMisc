"""Tests for brother_printer.usb_query - the PJL wire protocol.

The printer's fd is non-blocking throughout: usblp blocks forever on open
and on writes whenever the printer is unwell, which is exactly when a status
report is wanted. These tests pin that every read and write is bounded.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.usb_query import (
    _drain_buffer,
    _read_nonblocking,
    _wait_for_pjl_response,
    _write_with_deadline,
    pjl_query,
)

MOD = "python_pkg.brother_printer.usb_query"


class TestDrainBuffer:
    @patch(f"{MOD}.os.read")
    def test_drain(self, mock_read: MagicMock) -> None:
        mock_read.side_effect = [b"data", OSError("done")]
        _drain_buffer(42)
        assert mock_read.called

    @patch(f"{MOD}.os.read")
    def test_drain_empty_buffer(self, mock_read: MagicMock) -> None:
        """Buffer is already empty - os.read returns b'' immediately."""
        mock_read.return_value = b""
        _drain_buffer(42)
        mock_read.assert_called_once()


class TestReadNonblocking:
    @patch(f"{MOD}.os.read")
    def test_reads_chunks(self, mock_read: MagicMock) -> None:
        mock_read.side_effect = [b"hello", b"", OSError]
        assert _read_nonblocking(42) == b"hello"

    @patch(f"{MOD}.os.read")
    def test_oserror_suppressed(self, mock_read: MagicMock) -> None:
        mock_read.side_effect = OSError("would block")
        assert _read_nonblocking(42) == b""


class TestWriteWithDeadline:
    """Writes must never block forever on a printer that is not listening."""

    @patch(f"{MOD}.os.write", return_value=5)
    @patch(f"{MOD}.time.time", return_value=0.0)
    def test_writes_all(self, t: MagicMock, mock_write: MagicMock) -> None:
        assert _write_with_deadline(42, b"hello", 10.0) is True

    @patch(f"{MOD}.os.write")
    @patch(f"{MOD}.time.time", return_value=0.0)
    def test_partial_writes_resume(self, t: MagicMock, mock_write: MagicMock) -> None:
        mock_write.side_effect = [2, 3]
        assert _write_with_deadline(42, b"hello", 10.0) is True
        assert mock_write.call_count == 2

    @patch(f"{MOD}.time.time")
    def test_deadline_already_passed(self, mock_time: MagicMock) -> None:
        mock_time.return_value = 20.0
        assert _write_with_deadline(42, b"hello", 10.0) is False

    @patch(f"{MOD}.select.select", return_value=([], [], []))
    @patch(f"{MOD}.os.write", side_effect=BlockingIOError())
    @patch(f"{MOD}.time.time")
    def test_blocked_until_deadline(
        self,
        mock_time: MagicMock,
        mock_write: MagicMock,
        mock_select: MagicMock,
    ) -> None:
        """A printer that never accepts data times out instead of hanging."""
        mock_time.side_effect = [0.0, 1.0, 20.0]
        assert _write_with_deadline(42, b"hello", 10.0) is False

    @patch(f"{MOD}.select.select", return_value=([], [42], []))
    @patch(f"{MOD}.os.write")
    @patch(f"{MOD}.time.time", return_value=0.0)
    def test_blocked_then_writable(
        self,
        t: MagicMock,
        mock_write: MagicMock,
        mock_select: MagicMock,
    ) -> None:
        mock_write.side_effect = [BlockingIOError(), 5]
        assert _write_with_deadline(42, b"hello", 10.0) is True

    @patch(f"{MOD}.os.write", side_effect=OSError("gone"))
    @patch(f"{MOD}.time.time", return_value=0.0)
    def test_oserror_gives_up(self, t: MagicMock, mock_write: MagicMock) -> None:
        assert _write_with_deadline(42, b"hello", 10.0) is False


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
        assert b"CODE=10001" in _wait_for_pjl_response(42, 5.0)

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
        assert b"@PJL" in _wait_for_pjl_response(42, 5.0)

    @patch(f"{MOD}.select.select")
    @patch(f"{MOD}.time.time")
    def test_timeout_no_data(
        self,
        mock_time: MagicMock,
        mock_select: MagicMock,
    ) -> None:
        mock_time.side_effect = [10.0, 11.0]
        assert _wait_for_pjl_response(42, 5.0) == b""

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
        assert _wait_for_pjl_response(42, 5.0) == b""

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
        assert _wait_for_pjl_response(42, 5.0) == b""
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
        """Data read but no '=' or '@PJL' -> continues loop then times out."""
        mock_time.side_effect = [0.0, 0.5, 1.0, 6.0]
        mock_select.return_value = ([42], [], [])
        mock_read.return_value = b"garbage"
        assert _wait_for_pjl_response(42, 5.0) == b"garbage"


class TestPjlQuery:
    @patch(f"{MOD}._wait_for_pjl_response")
    @patch(f"{MOD}._write_with_deadline", return_value=True)
    @patch(f"{MOD}.time.time", return_value=100.0)
    def test_query(
        self,
        t: MagicMock,
        mock_write: MagicMock,
        mock_wait: MagicMock,
    ) -> None:
        mock_wait.return_value = b"CODE=10001"
        assert "CODE=10001" in pjl_query(42, "@PJL INFO STATUS")

    @patch(f"{MOD}._wait_for_pjl_response")
    @patch(f"{MOD}._write_with_deadline", return_value=False)
    @patch(f"{MOD}.time.time", return_value=100.0)
    def test_write_timeout_returns_empty(
        self,
        t: MagicMock,
        mock_write: MagicMock,
        mock_wait: MagicMock,
    ) -> None:
        """If we cannot even send the command, do not wait for a reply."""
        assert pjl_query(42, "@PJL INFO STATUS") == ""
        mock_wait.assert_not_called()

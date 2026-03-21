"""Tests for python_pkg.repo_explorer._execution."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from python_pkg.repo_explorer._execution import ExecutionMixin

if TYPE_CHECKING:
    import subprocess

# ── Protocol stub coverage ───────────────────────────────────────────


class TestProtocolStubs:
    def test_selected_path_stub(self) -> None:
        """Call the base stub to cover line 43."""
        result = ExecutionMixin._selected_path(MagicMock())
        assert result is None

    def test_after_stub(self) -> None:
        """Call the base stub to cover line 44."""
        result = ExecutionMixin.after(MagicMock(), 0)
        assert result is None


class StubExecution(ExecutionMixin):
    """Concrete stub for testing ExecutionMixin methods."""

    _IDLE_FLUSH_TICKS = 2

    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._master_fd: int | None = None
        self._terminal_args: list[str] = ["kitty", "--"]
        self._args_var = MagicMock(spec=tk.StringVar)
        self._stdin_var = MagicMock(spec=tk.StringVar)
        self._status_var = MagicMock(spec=tk.StringVar)
        self._run_btn = MagicMock(spec=ttk.Button)
        self._stop_btn = MagicMock(spec=ttk.Button)
        self._output = MagicMock(spec=tk.Text)
        self._path: Any = None
        self._after_calls: list[tuple[Any, ...]] = []

    def _selected_path(self) -> Any:
        return self._path

    def after(self, ms: int, *args: object) -> str:
        self._after_calls.append((ms, *args))
        return "after_id"


# ── _run_in_terminal ─────────────────────────────────────────────────


class TestRunInTerminal:
    def test_path_none_returns(self) -> None:
        obj = StubExecution()
        obj._path = None
        obj._run_in_terminal()
        assert obj._after_calls == []

    def test_no_terminal_args_returns(self) -> None:
        obj = StubExecution()
        obj._path = MagicMock()
        obj._terminal_args = []
        obj._run_in_terminal()
        assert obj._after_calls == []

    @patch("python_pkg.repo_explorer._execution.subprocess.Popen")
    def test_launches_with_args(self, mock_popen: MagicMock) -> None:
        obj = StubExecution()
        obj._path = MagicMock()
        obj._args_var.get.return_value = " --flag value "
        obj._run_in_terminal()
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd[:2] == ["kitty", "--"]
        assert "bash" in cmd
        assert "--flag" in cmd
        assert "value" in cmd

    @patch("python_pkg.repo_explorer._execution.subprocess.Popen")
    def test_launches_no_extra_args(self, mock_popen: MagicMock) -> None:
        obj = StubExecution()
        obj._path = MagicMock()
        obj._args_var.get.return_value = "  "
        obj._run_in_terminal()
        cmd = mock_popen.call_args[0][0]
        assert cmd == ["kitty", "--", "bash", "run.sh"]


# ── _run_embedded ────────────────────────────────────────────────────


class TestRunEmbedded:
    def test_path_none_returns(self) -> None:
        obj = StubExecution()
        obj._path = None
        obj._run_embedded()
        assert obj._run_btn.configure.call_count == 0

    @patch("python_pkg.repo_explorer._execution.threading.Thread")
    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.fcntl.fcntl")
    @patch("python_pkg.repo_explorer._execution.pty.openpty", return_value=(5, 6))
    @patch("python_pkg.repo_explorer._execution.subprocess.Popen")
    def test_runs_new_process(
        self,
        mock_popen: MagicMock,
        mock_openpty: MagicMock,
        mock_fcntl: MagicMock,
        mock_os_close: MagicMock,
        mock_thread: MagicMock,
    ) -> None:
        obj = StubExecution()
        obj._path = MagicMock()
        obj._args_var.get.return_value = ""
        obj._run_embedded()
        assert obj._master_fd == 5
        mock_os_close.assert_called_once_with(6)
        mock_popen.assert_called_once()
        assert mock_thread.call_count == 2

    @patch("python_pkg.repo_explorer._execution.threading.Thread")
    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.fcntl.fcntl")
    @patch("python_pkg.repo_explorer._execution.pty.openpty", return_value=(5, 6))
    @patch("python_pkg.repo_explorer._execution.subprocess.Popen")
    def test_stops_existing_then_runs(
        self,
        mock_popen: MagicMock,
        mock_openpty: MagicMock,
        mock_fcntl: MagicMock,
        mock_os_close: MagicMock,
        mock_thread: MagicMock,
    ) -> None:
        obj = StubExecution()
        obj._path = MagicMock()
        obj._args_var.get.return_value = "arg1 arg2"
        old_proc = MagicMock()
        old_proc.poll.return_value = None
        obj._proc = old_proc
        obj._run_embedded()
        old_proc.terminate.assert_called_once()

    @patch("python_pkg.repo_explorer._execution.threading.Thread")
    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.fcntl.fcntl")
    @patch("python_pkg.repo_explorer._execution.pty.openpty", return_value=(5, 6))
    @patch("python_pkg.repo_explorer._execution.subprocess.Popen")
    def test_existing_proc_already_exited(
        self,
        mock_popen: MagicMock,
        mock_openpty: MagicMock,
        mock_fcntl: MagicMock,
        mock_os_close: MagicMock,
        mock_thread: MagicMock,
    ) -> None:
        obj = StubExecution()
        obj._path = MagicMock()
        obj._args_var.get.return_value = ""
        old_proc = MagicMock()
        old_proc.poll.return_value = 0  # already exited
        obj._proc = old_proc
        obj._run_embedded()
        old_proc.terminate.assert_not_called()


# ── _decode_buf ──────────────────────────────────────────────────────


class TestDecodeBuf:
    def test_plain_text(self) -> None:
        assert ExecutionMixin._decode_buf(b"hello world") == "hello world"

    def test_ansi_stripped(self) -> None:
        assert ExecutionMixin._decode_buf(b"\x1b[31mred\x1b[0m") == "red"

    def test_carriage_return_removed(self) -> None:
        assert ExecutionMixin._decode_buf(b"line\r\n") == "line\n"

    def test_invalid_utf8(self) -> None:
        result = ExecutionMixin._decode_buf(b"\xff\xfe")
        assert isinstance(result, str)


# ── _flush_partial_buf ───────────────────────────────────────────────


class TestFlushPartialBuf:
    def test_non_empty_text(self) -> None:
        obj = StubExecution()
        obj._flush_partial_buf(b"hello")
        assert len(obj._after_calls) == 1

    def test_empty_after_strip(self) -> None:
        obj = StubExecution()
        obj._flush_partial_buf(b"\x1b[0m")
        assert obj._after_calls == []


# ── _process_complete_lines ──────────────────────────────────────────


class TestProcessCompleteLines:
    def test_complete_line(self) -> None:
        obj = StubExecution()
        remainder = obj._process_complete_lines(b"line1\nrest")
        assert remainder == b"rest"
        assert len(obj._after_calls) == 1

    def test_multiple_lines(self) -> None:
        obj = StubExecution()
        remainder = obj._process_complete_lines(b"a\nb\nc")
        assert remainder == b"c"
        assert len(obj._after_calls) == 2

    def test_no_newline(self) -> None:
        obj = StubExecution()
        remainder = obj._process_complete_lines(b"partial")
        assert remainder == b"partial"
        assert obj._after_calls == []

    def test_empty_line_skipped(self) -> None:
        obj = StubExecution()
        remainder = obj._process_complete_lines(b"\x1b[0m\nrest")
        assert remainder == b"rest"
        # ANSI-only line decodes to empty → not written
        assert obj._after_calls == []


# ── _read_pty ────────────────────────────────────────────────────────


class TestReadPty:
    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.os.read")
    @patch("python_pkg.repo_explorer._execution.select.select")
    def test_reads_data_and_exits(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        obj = StubExecution()
        proc = MagicMock()
        poll_values = iter([None, None, 0])
        proc.poll.side_effect = lambda: next(poll_values)
        obj._proc = proc
        obj._master_fd = 10

        mock_select.return_value = ([10], [], [])
        mock_read.return_value = b"hello\n"

        obj._read_pty()
        mock_close.assert_called_once_with(10)
        assert obj._master_fd is None

    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.os.read")
    @patch("python_pkg.repo_explorer._execution.select.select")
    def test_master_fd_none_breaks(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        obj = StubExecution()
        proc = MagicMock()
        proc.poll.return_value = None
        obj._proc = proc
        obj._master_fd = None

        obj._read_pty()
        mock_close.assert_not_called()

    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.os.read")
    @patch("python_pkg.repo_explorer._execution.select.select")
    def test_oserror_on_read_breaks(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        obj = StubExecution()
        proc = MagicMock()
        proc.poll.return_value = None
        obj._proc = proc
        obj._master_fd = 10

        mock_select.return_value = ([10], [], [])
        mock_read.side_effect = OSError("read error")

        obj._read_pty()
        mock_close.assert_called_once_with(10)

    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.os.read")
    @patch("python_pkg.repo_explorer._execution.select.select")
    def test_empty_chunk_breaks(
        self,
        mock_select: MagicMock,
        mock_read: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        obj = StubExecution()
        proc = MagicMock()
        proc.poll.return_value = None
        obj._proc = proc
        obj._master_fd = 10

        mock_select.return_value = ([10], [], [])
        mock_read.return_value = b""

        obj._read_pty()
        mock_close.assert_called_once_with(10)

    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.select.select")
    def test_idle_flushes_partial_buf(
        self,
        mock_select: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        obj = StubExecution()
        obj._IDLE_FLUSH_TICKS = 2
        proc = MagicMock()
        # poll returns None for idle iterations then exits
        poll_vals = iter([None, None, None, 0])
        proc.poll.side_effect = lambda: next(poll_vals)
        obj._proc = proc
        obj._master_fd = 10

        read_calls = [0]

        def fake_select(rlist: list[int], *_a: Any, **_kw: Any) -> Any:
            read_calls[0] += 1
            if read_calls[0] == 1:
                # First call: return data (no newline → stays in buf)
                return ([10], [], [])
            return ([], [], [])  # Subsequent: not ready (idle)

        mock_select.side_effect = fake_select

        with patch(
            "python_pkg.repo_explorer._execution.os.read",
            return_value=b"prompt> ",
        ):
            obj._read_pty()

        # buf should have been flushed
        assert any("prompt>" in str(c) for c in obj._after_calls)

    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.select.select")
    def test_idle_no_buf_continues(
        self,
        mock_select: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        obj = StubExecution()
        proc = MagicMock()
        poll_vals = iter([None, 0])
        proc.poll.side_effect = lambda: next(poll_vals)
        obj._proc = proc
        obj._master_fd = 10

        mock_select.return_value = ([], [], [])
        obj._read_pty()
        # No writes since no data
        assert obj._after_calls == []

    @patch("python_pkg.repo_explorer._execution.os.close")
    @patch("python_pkg.repo_explorer._execution.select.select")
    def test_idle_tick_under_threshold(
        self,
        mock_select: MagicMock,
        mock_close: MagicMock,
    ) -> None:
        """Idle tick < _IDLE_FLUSH_TICKS should NOT flush."""
        obj = StubExecution()
        obj._IDLE_FLUSH_TICKS = 5  # high threshold
        proc = MagicMock()
        poll_vals = iter([None, None, None, 0])
        proc.poll.side_effect = lambda: next(poll_vals)
        obj._proc = proc
        obj._master_fd = 10

        call_count = [0]

        def fake_select(rlist: list[int], *_a: Any, **_kw: Any) -> Any:
            call_count[0] += 1
            if call_count[0] == 1:
                return ([10], [], [])
            return ([], [], [])

        mock_select.side_effect = fake_select

        with patch(
            "python_pkg.repo_explorer._execution.os.read",
            return_value=b"data",
        ):
            obj._read_pty()
        # Final buf flush still happens at end
        assert any("data" in str(c) for c in obj._after_calls)

    @patch("python_pkg.repo_explorer._execution.os.close")
    def test_close_oserror_suppressed(
        self,
        mock_close: MagicMock,
    ) -> None:
        obj = StubExecution()
        proc = MagicMock()
        proc.poll.return_value = 1
        obj._proc = proc
        obj._master_fd = 10
        mock_close.side_effect = OSError("close error")
        obj._read_pty()
        assert obj._master_fd is None

    def test_proc_none_skips_loop(self) -> None:
        obj = StubExecution()
        obj._proc = None
        obj._master_fd = 10
        obj._read_pty()
        # master_fd might be set to None if code tries to close
        # but since _proc is None, the while loop is never entered


# ── _send_stdin ──────────────────────────────────────────────────────


class TestSendStdin:
    @patch("python_pkg.repo_explorer._execution.os.write")
    def test_writes_to_master_fd(self, mock_write: MagicMock) -> None:
        obj = StubExecution()
        obj._master_fd = 10
        obj._stdin_var.get.return_value = "hello"
        obj._send_stdin()
        mock_write.assert_called_once_with(10, b"hello\n")
        obj._stdin_var.set.assert_called_once_with("")

    def test_no_master_fd(self) -> None:
        obj = StubExecution()
        obj._master_fd = None
        obj._stdin_var.get.return_value = "hello"
        obj._send_stdin()
        obj._stdin_var.set.assert_called_once_with("")

    @patch("python_pkg.repo_explorer._execution.os.write")
    def test_oserror_suppressed(self, mock_write: MagicMock) -> None:
        obj = StubExecution()
        obj._master_fd = 10
        obj._stdin_var.get.return_value = "hello"
        mock_write.side_effect = OSError("write failed")
        obj._send_stdin()  # should not raise

    def test_with_event_arg(self) -> None:
        obj = StubExecution()
        obj._master_fd = None
        obj._stdin_var.get.return_value = "test"
        obj._send_stdin(MagicMock())
        obj._stdin_var.set.assert_called_once_with("")


# ── _wait_proc ───────────────────────────────────────────────────────


class TestWaitProc:
    def test_waits_and_calls_after(self) -> None:
        obj = StubExecution()
        proc = MagicMock()
        proc.wait.return_value = 0
        obj._proc = proc
        obj._wait_proc()
        proc.wait.assert_called_once()
        assert len(obj._after_calls) == 1

    def test_proc_none(self) -> None:
        obj = StubExecution()
        obj._proc = None
        obj._wait_proc()
        assert obj._after_calls == []


# ── _on_proc_done ────────────────────────────────────────────────────

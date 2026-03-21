"""Tests for _on_proc_done, _stop, _clear, _write_output, _append_output."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from python_pkg.repo_explorer._execution import ExecutionMixin

if TYPE_CHECKING:
    import subprocess


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


# ── _on_proc_done ────────────────────────────────────────────────────


class TestOnProcDone:
    def test_exit_code_zero(self) -> None:
        obj = StubExecution()
        obj._on_proc_done(0)
        obj._status_var.set.assert_called_once_with("✓ done")
        obj._run_btn.configure.assert_called_once_with(state=tk.NORMAL)
        obj._stop_btn.configure.assert_called_once_with(state=tk.DISABLED)
        assert any("exited with code 0" in str(c) for c in obj._after_calls)

    def test_exit_code_nonzero(self) -> None:
        obj = StubExecution()
        obj._on_proc_done(1)
        obj._status_var.set.assert_called_once_with("✗ exit 1")
        obj._run_btn.configure.assert_called_once_with(state=tk.NORMAL)
        obj._stop_btn.configure.assert_called_once_with(state=tk.DISABLED)
        assert any("exited with code 1" in str(c) for c in obj._after_calls)


# ── _stop ────────────────────────────────────────────────────────────


class TestStop:
    def test_proc_none(self) -> None:
        obj = StubExecution()
        obj._proc = None
        obj._stop()
        obj._status_var.set.assert_not_called()

    def test_proc_already_exited(self) -> None:
        obj = StubExecution()
        proc = MagicMock()
        proc.poll.return_value = 0
        obj._proc = proc
        obj._stop()
        proc.terminate.assert_not_called()
        obj._status_var.set.assert_not_called()


# ── _clear ───────────────────────────────────────────────────────────


class TestClear:
    def test_clears_output(self) -> None:
        obj = StubExecution()
        obj._clear()
        obj._output.configure.assert_any_call(state=tk.NORMAL)
        obj._output.delete.assert_called_once_with("1.0", tk.END)
        obj._output.configure.assert_any_call(state=tk.DISABLED)
        obj._status_var.set.assert_called_once_with("")


# ── _write_output ────────────────────────────────────────────────────


class TestWriteOutput:
    def test_write_output_with_tag(self) -> None:
        obj = StubExecution()
        obj._write_output("hello", "info")
        assert len(obj._after_calls) == 1

    def test_write_output_no_tag(self) -> None:
        obj = StubExecution()
        obj._write_output("hello")
        assert len(obj._after_calls) == 1


# ── _append_output ───────────────────────────────────────────────────


class TestAppendOutput:
    def test_append_with_tag(self) -> None:
        obj = StubExecution()
        obj._append_output("hello", "info")
        obj._output.configure.assert_any_call(state=tk.NORMAL)
        obj._output.insert.assert_called_once_with(tk.END, "hello", "info")
        obj._output.see.assert_called_once_with(tk.END)
        obj._output.configure.assert_any_call(state=tk.DISABLED)

    def test_append_without_tag(self) -> None:
        obj = StubExecution()
        obj._append_output("world", None)
        obj._output.insert.assert_called_once_with(tk.END, "world")
        obj._output.see.assert_called_once_with(tk.END)

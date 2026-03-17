"""Process execution mixin for Repo Explorer (embedded PTY and terminal)."""

from __future__ import annotations

import contextlib
import fcntl
import os
import pty
import select
import subprocess
import threading
import tkinter as tk
from typing import TYPE_CHECKING

from python_pkg.repo_explorer._discovery import REPO_ROOT, _strip_ansi

if TYPE_CHECKING:
    from pathlib import Path


class ExecutionMixin:
    """Mixin providing process launch, PTY streaming and stdin forwarding.

    Expects the concrete class to define: ``_proc``, ``_master_fd``,
    ``_terminal_args``, ``_args_var``, ``_stdin_var``, ``_status_var``,
    ``_run_btn``, ``_stop_btn``, ``_output``, ``_IDLE_FLUSH_TICKS``,
    ``_selected_path``, and the tkinter ``after`` method.
    """

    # Attributes provided by the concrete class (declared for type checkers)
    _proc: subprocess.Popen[bytes] | None
    _master_fd: int | None
    _terminal_args: list[str]
    _args_var: tk.StringVar
    _stdin_var: tk.StringVar
    _status_var: tk.StringVar
    _run_btn: ttk.Button  # type: ignore[name-defined]
    _stop_btn: ttk.Button  # type: ignore[name-defined]
    _output: tk.Text
    _IDLE_FLUSH_TICKS: int

    def _selected_path(self) -> Path | None: ...
    def after(self, ms: int, *args: object) -> str: ...

    # ------------------------------------------------------------------
    # Run in external terminal
    # ------------------------------------------------------------------

    def _run_in_terminal(self) -> None:
        path = self._selected_path()
        if path is None or not self._terminal_args:
            return
        args_str = self._args_var.get().strip()
        extra = args_str.split() if args_str else []
        subprocess.Popen(
            [*self._terminal_args, "bash", "run.sh", *extra], cwd=path
        )
        self._write_output(
            f"$ Launched in {self._terminal_args[0]}: "
            f"{path.relative_to(REPO_ROOT)}\n",
            "info",
        )

    # ------------------------------------------------------------------
    # Run embedded with PTY
    # ------------------------------------------------------------------

    def _run_embedded(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        if self._proc and self._proc.poll() is None:
            self._stop()

        self._clear()
        args_str = self._args_var.get().strip()
        extra = args_str.split() if args_str else []
        display_cmd = ("bash run.sh " + args_str).strip()
        self._write_output(
            f"$ {display_cmd}  [{path.relative_to(REPO_ROOT)}]\n", "info"
        )

        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd
        fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self._proc = subprocess.Popen(
            ["/usr/bin/bash", "run.sh", *extra],
            cwd=path,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)

        self._run_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)
        self._status_var.set("● running")

        threading.Thread(target=self._read_pty, daemon=True).start()
        threading.Thread(target=self._wait_proc, daemon=True).start()

    @staticmethod
    def _decode_buf(buf: bytes) -> str:
        """Decode a byte buffer, strip ANSI codes and carriage returns."""
        return _strip_ansi(buf.decode("utf-8", errors="replace").replace("\r", ""))

    def _flush_partial_buf(self, buf: bytes) -> None:
        """Flush a partial (no trailing newline) buffer to output."""
        text = self._decode_buf(buf)
        if text:
            self._write_output(text)

    def _process_complete_lines(self, buf: bytes) -> bytes:
        """Split buf on newlines, output complete lines, return remainder."""
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = self._decode_buf(line)
            if text:
                self._write_output(text + "\n")
        return buf

    def _read_pty(self) -> None:
        """Stream PTY output to the widget, stripping ANSI codes.

        Partial lines (prompts without a trailing newline) are flushed after
        ~100 ms of silence so interactive prompts like "Enter value: " appear.
        """
        buf = b""
        idle_ticks = 0
        while self._proc and self._proc.poll() is None:
            mfd = self._master_fd
            if mfd is None:
                break
            ready, _, _ = select.select([mfd], [], [], 0.05)
            if not ready:
                if buf:
                    idle_ticks += 1
                    if idle_ticks >= self._IDLE_FLUSH_TICKS:
                        self._flush_partial_buf(buf)
                        buf = b""
                        idle_ticks = 0
                continue
            idle_ticks = 0
            try:
                chunk = os.read(mfd, 4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            buf = self._process_complete_lines(buf)
        if buf:
            self._flush_partial_buf(buf)
        if self._master_fd is not None:
            with contextlib.suppress(OSError):
                os.close(self._master_fd)
            self._master_fd = None

    # ------------------------------------------------------------------
    # stdin forwarding
    # ------------------------------------------------------------------

    def _send_stdin(self, _event: object = None) -> None:
        text = self._stdin_var.get()
        self._stdin_var.set("")
        payload = (text + "\n").encode()
        if self._master_fd is not None:
            with contextlib.suppress(OSError):
                os.write(self._master_fd, payload)

    def _wait_proc(self) -> None:
        if self._proc:
            code = self._proc.wait()
            self.after(0, self._on_proc_done, code)

    def _on_proc_done(self, code: int) -> None:
        if code == 0:
            self._write_output(f"\n[exited with code {code}]\n", "success")
            self._status_var.set("✓ done")
        else:
            self._write_output(f"\n[exited with code {code}]\n", "error")
            self._status_var.set(f"✗ exit {code}")
        self._run_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.DISABLED)

    def _stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._status_var.set("stopped")

    def _clear(self) -> None:
        self._output.configure(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.configure(state=tk.DISABLED)
        self._status_var.set("")

    def _write_output(self, text: str, tag: str | None = None) -> None:
        """Thread-safe output append via after()."""
        self.after(0, self._append_output, text, tag)

    def _append_output(self, text: str, tag: str | None) -> None:
        self._output.configure(state=tk.NORMAL)
        if tag:
            self._output.insert(tk.END, text, tag)
        else:
            self._output.insert(tk.END, text)
        self._output.see(tk.END)
        self._output.configure(state=tk.DISABLED)

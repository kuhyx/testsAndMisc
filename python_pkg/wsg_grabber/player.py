"""Drives mpv as a subprocess embedded in a Tk frame, over its JSON IPC socket.

Not ``python-mpv``: that binding calls ``ctypes.util.find_library("mpv")`` at
import time and raises ``OSError`` wherever libmpv is absent, which includes
this repo's CI runner. It would pass locally and fail on push, and the usual
lazy-import escape trips ``PLC0415`` with no suppression available. A
subprocess needs only ``subprocess``, ``socket`` and ``json``.

``--wid`` is an mpv feature, so embedding behaves identically either way: mpv
reparents its own window onto the Tk frame and, per ``man mpv``, "will always be
resized to cover the parent window fully". That last part is why there is no
resize method here: setting ``geometry`` on an embedded mpv fights the
automatic sizing and leaves the video drawn at the wrong size.

``build_argv`` and ``encode`` are pure and tested directly. The rest is process
and socket handling: connecting, draining, and shutting down without leaving an
orphan. No reviewing decisions are made here.
"""

from __future__ import annotations

import json
import socket
import subprocess
import threading
import time
from typing import TYPE_CHECKING, Final, Protocol

from python_pkg.wsg_grabber import logs
from python_pkg.wsg_grabber.constants import IPC_READY_TIMEOUT_S

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_SOCKET_POLL_S = 0.05
_READ_CHUNK = 65536
_READ_TIMEOUT_S = 0.2
_READER_JOIN_S = 5.0
_PROBE_ID = 9001
_PROBE_TIMEOUT_S = 2.0

# What to record when diagnosing an apparently frozen reviewer: which file mpv
# holds, whether it is actually advancing, and the size it configured its video
# output to (which changes per video, so a static value is itself a symptom).
_PROBE_PROPERTIES: Final[tuple[str, ...]] = (
    "path",
    "pause",
    "core-idle",
    "eof-reached",
    "playback-time",
    "width",
    "height",
)


def _read_reply(conn: socket.socket) -> object:
    """Read until mpv answers the probe request.

    Args:
        conn: A freshly connected control socket.

    Returns:
        object: The ``data`` field of the reply, or an ``error:`` string.
    """
    buffer = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            return "error: socket closed"
        buffer += chunk
        for line in buffer.split(b"\n"):
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("request_id") == _PROBE_ID:
                return message.get("data")


class Player(Protocol):
    """What the reviewer needs from a video player."""

    def play(self, path: Path) -> None:
        """Show *path*, replacing whatever is on screen.

        Args:
            path: Video file to play.
        """
        ...  # pragma: no cover

    def stop(self) -> None:
        """Blank the video area."""
        ...  # pragma: no cover

    def is_alive(self) -> bool:
        """Report whether the player is still running.

        Returns:
            bool: True while the process lives.
        """
        ...  # pragma: no cover

    def probe(self) -> dict[str, object]:
        """Report what the player is currently doing, for diagnostics.

        Returns:
            dict[str, object]: Property name to value.
        """
        ...  # pragma: no cover

    def close(self) -> None:
        """Shut the player down and release its resources."""
        ...  # pragma: no cover


def build_argv(wid: int, ipc_path: Path) -> list[str]:
    """Build the mpv command line.

    ``--input-vo-keyboard=no`` matters: with ``--wid`` mpv reparents a child
    window over the Tk frame, and if mpv claims the keyboard the Tk bindings
    never see a keypress. Declining it leaves X delivering keys to the focused
    toplevel, which is the Tk window.

    Args:
        wid: X11 window id of the frame to draw into.
        ipc_path: Where to create the control socket.

    Returns:
        list[str]: Argument vector for :func:`subprocess.Popen`.
    """
    return [
        "mpv",
        f"--wid={wid}",
        f"--input-ipc-server={ipc_path}",
        "--idle=yes",
        "--loop-file=inf",
        "--keep-open=yes",
        "--no-terminal",
        "--osc=no",
        "--input-default-bindings=no",
        "--input-vo-keyboard=no",
        "--no-config",
    ]


def encode(command: Sequence[object]) -> bytes:
    """Encode one mpv IPC command.

    Args:
        command: Command name followed by its arguments.

    Returns:
        bytes: Newline-terminated JSON, ready for the socket.
    """
    return json.dumps({"command": list(command)}).encode("utf-8") + b"\n"


class MpvPlayer:
    """An mpv process drawing into a Tk frame."""

    def __init__(self, wid: int, ipc_path: Path) -> None:
        """Start mpv and connect to its control socket.

        Args:
            wid: X11 window id of the frame to draw into.
            ipc_path: Where mpv should create its control socket.

        Raises:
            TimeoutError: If mpv does not create the socket in time, which
                means it failed to start and there is nothing to talk to.
            OSError: If the socket exists but refuses the connection, e.g. a
                stale file left by a previous run.
        """
        ipc_path.unlink(missing_ok=True)
        ipc_path.parent.mkdir(parents=True, exist_ok=True)
        self._ipc_path = ipc_path
        argv = build_argv(wid, ipc_path)
        logs.event("player.start", wid=wid, socket=str(ipc_path), argv=argv)
        self._process = subprocess.Popen(argv)
        try:
            self._socket = self._connect()
        except BaseException:
            # Reaping matters as much as killing: an unwaited child stays a
            # zombie, and the caller is about to abandon this object entirely.
            self._process.kill()
            self._process.wait(timeout=IPC_READY_TIMEOUT_S)
            raise
        self._stopping = threading.Event()
        self._reader = threading.Thread(
            target=self._drain,
            name="mpv-ipc-reader",
            daemon=False,
        )
        self._reader.start()
        logs.event("player.ready", pid=self._process.pid)

    def _drain(self) -> None:
        """Continuously read and discard what mpv sends us.

        This is not optional bookkeeping, it is what keeps the player working.
        mpv pushes an asynchronous event stream plus a reply per command down
        the same socket. A client that only ever writes lets that backlog fill
        the kernel buffer; mpv's writer for this connection then blocks, and it
        stops reading our commands. The symptom is nasty because nothing
        errors: ``sendall`` still succeeds, mpv stays alive and keeps playing
        whatever it had, so the reviewer advances through filenames while the
        picture never changes. Measured before this existed: commands were
        silently ignored from roughly the thirty-fifth video onwards, while the
        very same command sent on a fresh connection worked instantly.

        Replies carrying an error are logged, which is also how a file mpv
        cannot decode becomes visible instead of just looking stuck.
        """
        while not self._stopping.is_set():
            try:
                chunk = self._socket.recv(_READ_CHUNK)
            except TimeoutError:
                continue
            except OSError:
                return
            if not chunk:
                return
            self._note_errors(chunk)

    def _note_errors(self, chunk: bytes) -> None:
        """Log any failure mpv reported back.

        Args:
            chunk: Raw bytes just read from the socket.
        """
        for line in chunk.split(b"\n"):
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            failure = message.get("error")
            if isinstance(failure, str) and failure != "success":
                logs.warning("player.reply_error", detail=failure, reply=message)

    def _connect(self) -> socket.socket:
        """Wait for mpv's socket to appear and connect to it.

        Returns:
            socket.socket: Connected unix socket.

        Raises:
            TimeoutError: If the socket never appears.
            OSError: If connecting to it fails.
        """
        deadline = time.monotonic() + IPC_READY_TIMEOUT_S
        while not self._ipc_path.exists():
            if time.monotonic() >= deadline:
                # __init__ owns killing and reaping the process on every
                # failure path; doing it here too would just double up.
                msg = f"mpv did not create {self._ipc_path} within the timeout"
                raise TimeoutError(msg)
            time.sleep(_SOCKET_POLL_S)
        control = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            control.connect(str(self._ipc_path))
        except BaseException:
            control.close()
            raise
        # so the reader thread can notice the stop flag rather than
        # blocking in recv() forever at shutdown
        control.settimeout(_READ_TIMEOUT_S)
        return control

    def _send(self, command: Sequence[object]) -> None:
        """Write a command to mpv.

        A failure here is logged rather than raised -- mpv may simply have
        exited, and is_alive() reports that to the caller -- but it is never
        silently discarded, because a dead socket makes a working reviewer and
        a frozen one look identical from the outside.

        Args:
            command: Command name followed by its arguments.
        """
        try:
            self._socket.sendall(encode(command))
        except OSError as exc:
            logs.error(
                "player.send_failed",
                command=list(command),
                detail=str(exc),
                alive=self.is_alive(),
            )
            return
        logs.debug("player.command", command=list(command))

    def play(self, path: Path) -> None:
        """Show *path*, replacing whatever is on screen.

        Args:
            path: Video file to play.
        """
        logs.event("player.load", file=path.name, path=str(path), exists=path.exists())
        self._send(["loadfile", str(path), "replace"])

    def stop(self) -> None:
        """Blank the video area."""
        self._send(["stop"])

    def probe(self) -> dict[str, object]:
        """Ask mpv what it is actually doing.

        This exists for after-the-fact diagnosis. If the reviewer ever appears
        to freeze on one video while the filenames advance, the recorded answer
        settles in one line whether mpv was handed the new file and was
        decoding it, or whether the problem is upstream of mpv.

        Returns:
            dict[str, object]: Property name to value; a property that could
            not be read maps to a string starting with ``error:``.
        """
        return {name: self._query(name) for name in _PROBE_PROPERTIES}

    def _query(self, name: str) -> object:
        """Read one mpv property over a short-lived connection.

        A separate connection avoids interleaving with the asynchronous events
        mpv pushes down the main socket, which would otherwise make replies
        easy to mis-attribute.

        Args:
            name: Property name.

        Returns:
            object: The value, or an ``error:`` string.
        """
        request = json.dumps(
            {"command": ["get_property", name], "request_id": _PROBE_ID}
        )
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(_PROBE_TIMEOUT_S)
                probe.connect(str(self._ipc_path))
                probe.sendall(request.encode("utf-8") + b"\n")
                return _read_reply(probe)
        except OSError as exc:
            return f"error: {exc}"

    def is_alive(self) -> bool:
        """Report whether mpv is still running.

        Returns:
            bool: True while the process lives.
        """
        return self._process.poll() is None

    def close(self) -> None:
        """Ask mpv to quit, then make sure it has.

        Leaving an orphaned mpv behind would keep a window on screen after the
        reviewer exits, so a process that ignores ``quit`` is killed.
        """
        logs.event("player.close", alive=self.is_alive())
        self._stopping.set()
        self._send(["quit"])
        try:
            self._process.wait(timeout=IPC_READY_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=IPC_READY_TIMEOUT_S)
        self._reader.join(timeout=_READER_JOIN_S)
        self._socket.close()
        self._ipc_path.unlink(missing_ok=True)

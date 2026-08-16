"""Talking to mpv: the command line, the wire format, and the reply reader.

Split out of :mod:`python_pkg.wsg_grabber.player` to keep it under the 250-line
cap. Everything here is stateless -- it does not own the process or the socket,
only the shapes of what goes over them.
"""

from __future__ import annotations

import json
import socket
from typing import TYPE_CHECKING, Final

from python_pkg.wsg_grabber import logs

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

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


def read_reply(conn: socket.socket) -> object:
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


def note_errors(chunk: bytes) -> None:
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


def probe_properties(ipc_path: Path) -> dict[str, object]:
    """Ask mpv for each diagnostic property in turn.

    Args:
        ipc_path: Where mpv's control socket lives.

    Returns:
        dict[str, object]: Property name to value; a property that could not
        be read maps to a string starting with ``error:``.
    """
    return {name: query(ipc_path, name) for name in _PROBE_PROPERTIES}


def query(ipc_path: Path, name: str) -> object:
    """Read one mpv property over a short-lived connection.

    A separate connection avoids interleaving with the asynchronous events mpv
    pushes down the main socket, which would otherwise make replies easy to
    mis-attribute.

    Args:
        ipc_path: Where mpv's control socket lives.
        name: Property name.

    Returns:
        object: The value, or an ``error:`` string.
    """
    request = json.dumps({"command": ["get_property", name], "request_id": _PROBE_ID})
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(_PROBE_TIMEOUT_S)
            probe.connect(str(ipc_path))
            probe.sendall(request.encode("utf-8") + b"\n")
            return read_reply(probe)
    except OSError as exc:
        return f"error: {exc}"

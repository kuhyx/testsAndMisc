"""Tests for how the player reports IPC failures."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import logs, player

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def _socket_mock(**kwargs: object) -> MagicMock:
    """Build a socket stand-in whose reader thread terminates immediately.

    An unconfigured MagicMock returns a MagicMock from recv(), which is truthy
    and instant, so the drain loop spins as fast as the CPU allows -- and
    MagicMock records every call, so memory grows without bound. That once
    reached 21 GB and took the machine down, hence this helper: every socket
    mock yields EOF unless a test deliberately says otherwise.

    Args:
        **kwargs: Attributes to set on the mock.

    Returns:
        MagicMock: Socket double.
    """
    sock = MagicMock()
    sock.recv.return_value = b""
    for name, value in kwargs.items():
        setattr(sock, name, value)
    return sock


@pytest.fixture(autouse=True)
def _safe_sockets() -> Iterator[None]:
    """Stop a stray socket mock from turning the drain loop into a busy loop.

    ``MpvPlayer`` runs a reader thread that calls ``recv`` until EOF. An
    unconfigured MagicMock returns a MagicMock -- truthy, instant, and it
    records every call -- so the loop spins and memory grows without bound.
    That once reached 21 GB and OOM-killed the machine. Defaulting the module's
    socket factory to something that reports EOF means a test has to opt into
    the hazard deliberately.

    Yields:
        None: Control returns to the test.
    """
    with patch(
        "python_pkg.wsg_grabber.player.socket.socket",
        side_effect=lambda *_a, **_k: _socket_mock(),
    ):
        yield


@pytest.fixture
def started(tmp_path: Path) -> Iterator[tuple[player.MpvPlayer, MagicMock, MagicMock]]:
    """Construct an MpvPlayer with its process and socket mocked out.

    Args:
        tmp_path: Per-test temporary directory.

    Yields:
        tuple: The player, its process mock and its socket mock.
    """
    ipc = tmp_path / "mpv.sock"
    process = MagicMock()
    process.poll.return_value = None
    sock = _socket_mock()

    def create_socket(_seconds: float) -> None:
        """Stand in for mpv finally creating its control socket."""
        ipc.write_bytes(b"")

    # __init__ unlinks any stale socket first, so it has to appear *during*
    # the wait rather than being pre-created.
    with (
        patch("python_pkg.wsg_grabber.player.subprocess.Popen", return_value=process),
        patch("python_pkg.wsg_grabber.player.socket.socket", return_value=sock),
        patch("python_pkg.wsg_grabber.player.time.sleep", side_effect=create_socket),
    ):
        yield player.MpvPlayer(1234, ipc), process, sock


def test_a_failed_send_is_logged_not_swallowed(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
    tmp_path: Path,
) -> None:
    """A dead socket must not make a frozen reviewer look like a working one."""
    mpv, _process, sock = started
    sock.sendall.side_effect = BrokenPipeError("gone")
    log = logs.start("debug")
    try:
        mpv.play(tmp_path / "clip.webm")
    finally:
        logs.stop()
    recorded = [
        json.loads(line)
        for line in log.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert any(r["event"] == "player.send_failed" for r in recorded)
    assert any(r["level"] == "error" for r in recorded)


def test_the_socket_is_drained_so_mpv_keeps_accepting_commands(
    tmp_path: Path,
) -> None:
    """The regression that made the reviewer freeze on one video.

    mpv pushes events down the same socket; a client that never reads lets the
    buffer fill, at which point mpv stops reading commands while still looking
    perfectly alive.
    """
    ipc = tmp_path / "mpv.sock"
    process = MagicMock()
    process.poll.return_value = None
    sock = _socket_mock()
    seen: list[int] = []

    def recv(size: int) -> bytes:
        seen.append(size)
        return b'{"event":"property-change"}\n' if len(seen) < 3 else b""

    sock.recv.side_effect = recv

    with (
        patch("python_pkg.wsg_grabber.player.subprocess.Popen", return_value=process),
        patch("python_pkg.wsg_grabber.player.socket.socket", return_value=sock),
        patch(
            "python_pkg.wsg_grabber.player.time.sleep",
            side_effect=lambda _s: ipc.write_bytes(b""),
        ),
    ):
        mpv = player.MpvPlayer(1, ipc)
        mpv._reader.join(timeout=5)
        mpv.close()

    assert seen, "the reader never read from the socket"
    assert not mpv._reader.is_alive()


def test_the_reader_stops_on_a_socket_error(tmp_path: Path) -> None:
    ipc = tmp_path / "mpv.sock"
    process = MagicMock()
    process.poll.return_value = None
    sock = _socket_mock()
    sock.recv.side_effect = ConnectionResetError("gone")
    with (
        patch("python_pkg.wsg_grabber.player.subprocess.Popen", return_value=process),
        patch("python_pkg.wsg_grabber.player.socket.socket", return_value=sock),
        patch(
            "python_pkg.wsg_grabber.player.time.sleep",
            side_effect=lambda _s: ipc.write_bytes(b""),
        ),
    ):
        mpv = player.MpvPlayer(1, ipc)
        mpv._reader.join(timeout=5)
        assert not mpv._reader.is_alive()
        mpv.close()


def test_the_reader_keeps_going_through_read_timeouts(tmp_path: Path) -> None:
    """A quiet socket must not be mistaken for a closed one."""
    ipc = tmp_path / "mpv.sock"
    process = MagicMock()
    process.poll.return_value = None
    sock = _socket_mock()
    calls = {"n": 0}

    def recv(_size: int) -> bytes:
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError
        return b""

    sock.recv.side_effect = recv
    with (
        patch("python_pkg.wsg_grabber.player.subprocess.Popen", return_value=process),
        patch("python_pkg.wsg_grabber.player.socket.socket", return_value=sock),
        patch(
            "python_pkg.wsg_grabber.player.time.sleep",
            side_effect=lambda _s: ipc.write_bytes(b""),
        ),
    ):
        mpv = player.MpvPlayer(1, ipc)
        mpv._reader.join(timeout=5)
        mpv.close()
    assert calls["n"] >= 3


def test_mpv_errors_are_logged_rather_than_discarded(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    """A file mpv cannot decode should be visible, not just look stuck."""
    mpv, _process, _sock = started
    log = logs.start("debug")
    try:
        mpv._note_errors(
            b'{"error":"success"}\n'
            b"\n"
            b"garbage\n"
            b'{"request_id":1,"error":"loadfile failed"}\n',
        )
    finally:
        logs.stop()
    recorded = [
        json.loads(line)
        for line in log.read_text(encoding="utf-8").splitlines()
        if line
    ]
    failures = [r for r in recorded if r["event"] == "player.reply_error"]
    assert len(failures) == 1
    assert failures[0]["detail"] == "loadfile failed"

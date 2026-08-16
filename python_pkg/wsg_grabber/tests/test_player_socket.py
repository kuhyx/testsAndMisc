"""Tests for the socket stand-ins and connection teardown."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import player

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


def test_socket_stand_ins_always_report_eof() -> None:
    """The contract that keeps the reader thread from becoming a busy loop.

    A mock whose recv() returns a MagicMock is truthy and instant, so the drain
    loop spins and the mock's recorded-call list grows without bound -- 21 GB
    and an OOM kill, in the incident this guards against.
    """
    assert _socket_mock().recv(65536) == b""


def test_the_reader_returns_promptly_once_asked_to_stop(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    """Shutdown must not wait on another read."""
    mpv, _process, sock = started
    sock.recv.reset_mock()
    mpv._stopping.set()
    mpv._drain()
    sock.recv.assert_not_called()


def test_a_refused_connection_does_not_leak_the_socket(tmp_path: Path) -> None:
    """A stale socket file makes connect() fail; nothing may be left open."""
    ipc = tmp_path / "stale.sock"
    process = MagicMock()
    sock = _socket_mock()
    sock.connect.side_effect = ConnectionRefusedError("stale")

    with (
        patch("python_pkg.wsg_grabber.player.subprocess.Popen", return_value=process),
        patch("python_pkg.wsg_grabber.player.socket.socket", return_value=sock),
        patch(
            "python_pkg.wsg_grabber.player.time.sleep",
            side_effect=lambda _s: ipc.write_bytes(b""),
        ),
        pytest.raises(ConnectionRefusedError),
    ):
        player.MpvPlayer(1, ipc)

    sock.close.assert_called_once()
    process.kill.assert_called_once()
    process.wait.assert_called_once()  # reaped, not left a zombie

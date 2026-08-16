"""Tests for probing what mpv is doing over its IPC socket."""

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


def test_probe_reports_what_mpv_is_doing(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
    tmp_path: Path,
) -> None:
    """The answer that settles a 'it froze on one video' report."""
    mpv, _process, _sock = started
    reply = _socket_mock()
    reply.recv.return_value = (
        b'{"request_id": 9001, "data": "value", "error": "success"}\n'
    )
    reply.__enter__ = lambda self: self
    reply.__exit__ = lambda *_a: False
    with patch("python_pkg.wsg_grabber.player.socket.socket", return_value=reply):
        result = mpv.probe()
    assert set(result) == {
        "path",
        "pause",
        "core-idle",
        "eof-reached",
        "playback-time",
        "width",
        "height",
    }
    assert result["path"] == "value"


def test_probe_records_a_failure_rather_than_raising(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    mpv, _process, _sock = started
    with patch(
        "python_pkg.wsg_grabber.player.socket.socket",
        side_effect=ConnectionRefusedError("gone"),
    ):
        result = mpv.probe()
    assert all(str(value).startswith("error:") for value in result.values())


def test_probe_survives_a_socket_that_closes_early(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    mpv, _process, _sock = started
    reply = _socket_mock()
    reply.recv.return_value = b""
    reply.__enter__ = lambda self: self
    reply.__exit__ = lambda *_a: False
    with patch("python_pkg.wsg_grabber.player.socket.socket", return_value=reply):
        result = mpv.probe()
    assert result["path"] == "error: socket closed"


def test_probe_ignores_unrelated_traffic_on_the_socket(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    """mpv pushes async events down the socket; they must not be mistaken
    for the reply, and a partial line must not crash the reader."""
    mpv, _process, _sock = started
    reply = _socket_mock()
    reply.recv.side_effect = [
        b'{"event": "property-change"}\nnot json\n',
        b'{"request_id": 9001, "data": 42}\n',
    ] * 10
    reply.__enter__ = lambda self: self
    reply.__exit__ = lambda *_a: False
    with patch("python_pkg.wsg_grabber.player.socket.socket", return_value=reply):
        assert mpv.probe()["path"] == 42

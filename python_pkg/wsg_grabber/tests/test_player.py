"""Tests for the mpv subprocess driver.

No mpv binary is ever started: ``subprocess.Popen`` and ``socket.socket`` are
patched in the module's own namespace.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import player

if TYPE_CHECKING:
    from collections.abc import Iterator


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


def test_argv_embeds_into_the_given_window(tmp_path: Path) -> None:
    argv = player.build_argv(999, tmp_path / "s.sock")
    assert argv[0] == "mpv"
    assert "--wid=999" in argv
    assert f"--input-ipc-server={tmp_path / 's.sock'}" in argv


def test_argv_declines_the_keyboard_so_tk_can_have_it(tmp_path: Path) -> None:
    """With --wid mpv's child window would otherwise swallow every keypress."""
    argv = player.build_argv(1, tmp_path / "s.sock")
    assert "--input-vo-keyboard=no" in argv
    assert "--input-default-bindings=no" in argv


def test_argv_loops_and_stays_open(tmp_path: Path) -> None:
    argv = player.build_argv(1, tmp_path / "s.sock")
    assert "--loop-file=inf" in argv
    assert "--idle=yes" in argv
    assert "--keep-open=yes" in argv


def test_encode_produces_one_json_line() -> None:
    payload = player.encode(["loadfile", "a.webm", "replace"])
    assert payload.endswith(b"\n")
    assert json.loads(payload) == {
        "command": ["loadfile", "a.webm", "replace"],
    }


def test_play_sends_loadfile(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
    tmp_path: Path,
) -> None:
    mpv, _process, sock = started
    mpv.play(tmp_path / "clip.webm")
    sock.sendall.assert_called_once_with(
        player.encode(["loadfile", str(tmp_path / "clip.webm"), "replace"]),
    )


def test_stop_blanks_the_video(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    mpv, _process, sock = started
    mpv.stop()
    assert sock.sendall.call_args.args[0] == player.encode(["stop"])


def test_a_dead_socket_does_not_raise(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
    tmp_path: Path,
) -> None:
    """mpv can exit underneath us; is_alive reports that, sending must not blow up."""
    mpv, _process, sock = started
    sock.sendall.side_effect = BrokenPipeError("gone")
    mpv.play(tmp_path / "clip.webm")


def test_is_alive_follows_the_process(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    mpv, process, _sock = started
    assert mpv.is_alive()
    process.poll.return_value = 0
    assert not mpv.is_alive()


def test_close_quits_cleanly_and_removes_the_socket(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
    tmp_path: Path,
) -> None:
    mpv, process, sock = started
    mpv.close()
    assert sock.sendall.call_args.args[0] == player.encode(["quit"])
    process.wait.assert_called_once()
    process.kill.assert_not_called()
    sock.close.assert_called_once()
    assert not (tmp_path / "mpv.sock").exists()


def test_close_kills_an_mpv_that_ignores_quit(
    started: tuple[player.MpvPlayer, MagicMock, MagicMock],
) -> None:
    """An orphaned mpv would leave a window on screen after the reviewer exits."""
    mpv, process, _sock = started
    process.wait.side_effect = [subprocess.TimeoutExpired("mpv", 1), None]
    mpv.close()
    process.kill.assert_called_once()


def test_a_socket_that_never_appears_is_a_timeout(tmp_path: Path) -> None:
    ipc = tmp_path / "never.sock"
    process = MagicMock()
    with (
        patch("python_pkg.wsg_grabber.player.subprocess.Popen", return_value=process),
        patch("python_pkg.wsg_grabber.player.time.sleep"),
        patch(
            "python_pkg.wsg_grabber.player.time.monotonic",
            side_effect=[0.0, 0.0, 9999.0],
        ),
        pytest.raises(TimeoutError, match="did not create"),
    ):
        player.MpvPlayer(1, ipc)
    process.kill.assert_called_once()


def test_the_socket_is_awaited_rather_than_assumed(tmp_path: Path) -> None:
    """mpv takes a moment to create the socket; connecting too early fails."""
    ipc = tmp_path / "late.sock"
    process = MagicMock()
    sock = _socket_mock()
    waits = {"n": 0}

    def create_on_third_try(_seconds: float) -> None:
        waits["n"] += 1
        if waits["n"] >= 3:
            ipc.write_bytes(b"")

    with (
        patch("python_pkg.wsg_grabber.player.subprocess.Popen", return_value=process),
        patch("python_pkg.wsg_grabber.player.socket.socket", return_value=sock),
        patch(
            "python_pkg.wsg_grabber.player.time.sleep",
            side_effect=create_on_third_try,
        ),
    ):
        player.MpvPlayer(1, ipc)
    assert waits["n"] == 3


def test_the_player_never_sets_geometry() -> None:
    """--wid makes mpv fill its parent; setting geometry shrinks the video."""
    argv = player.build_argv(1, Path("sock"))
    assert not any(arg.startswith("--geometry") for arg in argv)
    assert not hasattr(player.MpvPlayer, "resize")

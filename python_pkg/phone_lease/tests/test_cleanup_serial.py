"""Cleanup command runner, the reaper launcher, and serial resolution."""

from __future__ import annotations

from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.phone_lease import NoPhoneError, _cleanup, resolve_serial
from python_pkg.phone_lease import serial as serial_mod


class TestRun:
    def test_codes_per_command_without_a_shell(self) -> None:
        done: list[subprocess.CompletedProcess[bytes]] = [
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 3),
        ]
        with patch(
            "python_pkg.phone_lease._cleanup.subprocess.run", side_effect=done
        ) as run:
            assert _cleanup.run(["adb shell 'a b'", "false"]) == [0, 3]
        assert run.call_args_list[0].args[0] == ["adb", "shell", "a b"]

    def test_failures_never_stop_the_rest(self) -> None:
        effects = [
            OSError("missing"),
            subprocess.TimeoutExpired("x", 30),
            subprocess.CompletedProcess([], 0),
        ]
        with patch(
            "python_pkg.phone_lease._cleanup.subprocess.run", side_effect=effects
        ):
            assert _cleanup.run(["nope", "slow", "ok"]) == [127, 127, 0]

    def test_unparseable_command(self) -> None:
        with patch("python_pkg.phone_lease._cleanup.subprocess.run") as run:
            assert _cleanup.run(["echo 'unterminated"]) == [127]
        run.assert_not_called()


def test_spawn_reaper_detaches_our_own_module() -> None:
    with patch("python_pkg.phone_lease._cleanup.subprocess.Popen") as popen:
        _cleanup.spawn_reaper("S", "claude:1", "whole-phone")
    argv = popen.call_args.args[0]
    assert argv[1:] == [
        "-m",
        "python_pkg.phone_lease",
        "reap",
        "S",
        "--owner",
        "claude:1",
        "--scope",
        "whole-phone",
    ]
    kwargs = popen.call_args.kwargs
    assert kwargs["start_new_session"] is True
    repo_root = Path(_cleanup.__file__).resolve().parents[2]
    assert kwargs["env"]["PYTHONPATH"] == str(repo_root)


class TestResolveSerial:
    def test_explicit_wins(self) -> None:
        assert resolve_serial("X", environ={"ANDROID_SERIAL": "Y"}) == "X"

    @pytest.mark.parametrize(
        ("env", "want"),
        [
            ({"ANDROID_SERIAL": "A", "ADB_SERIAL": "B"}, "A"),
            ({"ANDROID_SERIAL": "", "ADB_SERIAL": "B"}, "B"),
        ],
    )
    def test_environment(self, env: dict[str, str], want: str) -> None:
        assert resolve_serial(environ=env) == want

    def test_asks_adb_last(self) -> None:
        assert resolve_serial(environ={}, ask_adb=lambda: "USB1") == "USB1"

    @pytest.mark.parametrize("answer", ["", "unknown"])
    def test_no_single_phone(self, answer: str) -> None:
        with pytest.raises(NoPhoneError, match="no phone serial"):
            resolve_serial(environ={}, ask_adb=lambda: answer)

    def test_adb_crashing_is_no_phone(self) -> None:
        def boom() -> str:
            raise OSError

        with pytest.raises(NoPhoneError):
            resolve_serial(environ={}, ask_adb=boom)

    def test_real_environment_by_default(self) -> None:
        with patch.dict("os.environ", {"ANDROID_SERIAL": "ENV"}):
            assert resolve_serial() == "ENV"


class TestAdbSerial:
    def test_without_adb(self) -> None:
        with patch("python_pkg.phone_lease.serial.shutil.which", return_value=None):
            assert serial_mod._adb_serial() == ""

    @pytest.mark.parametrize(("code", "want"), [(0, "PHONE"), (1, "")])
    def test_asks_the_full_adb_path(self, code: int, want: str) -> None:
        done = MagicMock(returncode=code, stdout="PHONE\n")
        with (
            patch(
                "python_pkg.phone_lease.serial.shutil.which",
                return_value="/usr/bin/adb",
            ),
            patch(
                "python_pkg.phone_lease.serial.subprocess.run", return_value=done
            ) as run,
        ):
            assert serial_mod._adb_serial() == want
        assert run.call_args.args[0] == ["/usr/bin/adb", "get-serialno"]

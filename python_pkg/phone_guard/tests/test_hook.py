"""The PreToolUse hook: which Bash calls run, which lease first, which stop."""

from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.android_ui._elements import UiAutomationError
from python_pkg.phone_guard import hook
from python_pkg.phone_guard.tests.conftest import make_display
from python_pkg.phone_lease import NoPhoneError, PhoneBusyError

MOD = "python_pkg.phone_guard.hook"


def run(command: str, tool: str = "Bash") -> int:
    return hook.main(
        io.StringIO(json.dumps({"tool_name": tool, "tool_input": {"command": command}}))
    )


@pytest.fixture
def acquire() -> MagicMock:
    with (
        patch(f"{MOD}.acquire") as mock,
        patch(f"{MOD}.owner_id", return_value="claude:1"),
        patch(f"{MOD}.resolve_serial", side_effect=lambda s=None: s or "S"),
        patch(f"{MOD}.build_tool", side_effect=UiAutomationError("no sdk")),
    ):
        yield mock


class TestMain:
    def test_ignores_what_it_cannot_or_need_not_judge(self, acquire: MagicMock) -> None:
        assert hook.main(io.StringIO("not json")) == 0
        assert run("adb shell input tap 1 1", tool="Read") == 0
        assert run("ls -la") == 0
        assert hook.main(io.StringIO(json.dumps({"tool_name": "Bash"}))) == 0
        acquire.assert_not_called()

    def test_reads_pass_without_a_lease(self, acquire: MagicMock) -> None:
        assert run("adb logcat -d") == 0
        acquire.assert_not_called()

    def test_a_block_exits_2_with_the_reason(
        self, acquire: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert run("adb shell input text hi") == hook.BLOCK
        assert "without -d" in capsys.readouterr().err
        acquire.assert_not_called()


class TestLeases:
    def test_the_real_screen(self, acquire: MagicMock) -> None:
        assert run("adb shell input tap 1 1") == 0
        assert acquire.call_args.kwargs["scope"] == "pkg:__screen__"
        assert acquire.call_args.kwargs["owner"] == "claude:1"
        assert acquire.call_args.args[0] == "S"

    def test_the_whole_phone_and_an_app(self, acquire: MagicMock) -> None:
        assert run("adb -s X reboot && adb shell am force-stop a.b") == 0
        scopes = [c.kwargs["scope"] for c in acquire.call_args_list]
        assert scopes == ["whole-phone", "pkg:a.b"]
        assert acquire.call_args_list[0].args[0] == "X"

    def test_own_display_takes_its_app_lease(
        self, acquire: MagicMock, isolated_state: Path
    ) -> None:
        make_display(isolated_state, "S", "claude_1", "9", "dev.kuhy.todo")
        assert run("adb shell input -d 9 tap 5 5") == 0
        assert acquire.call_args.kwargs["scope"] == "pkg:dev.kuhy.todo"

    def test_another_sessions_display_is_refused(
        self,
        acquire: MagicMock,
        isolated_state: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        make_display(isolated_state, "S", "claude_2", "9", "x.y")
        assert run("adb shell input -d 9 tap 5 5") == hook.BLOCK
        assert "session claude_2's" in capsys.readouterr().err
        assert run("adb shell input -d 4 tap 5 5") == hook.BLOCK
        assert "not your" in capsys.readouterr().err
        acquire.assert_not_called()

    def test_busy_phone_blocks_naming_the_holder(
        self, acquire: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        acquire.side_effect = PhoneBusyError("held by claude:2")
        assert run("adb shell input tap 1 1") == hook.BLOCK
        err = capsys.readouterr().err
        assert "held by claude:2" in err
        assert "own virtual display" in err

    def test_no_resolvable_phone_is_left_to_adb(self, acquire: MagicMock) -> None:
        with patch(f"{MOD}.resolve_serial", side_effect=NoPhoneError("several")):
            assert run("adb shell input tap 1 1") == 0
        acquire.assert_not_called()


class TestApkPackages:
    def test_reads_the_package_with_aapt2(self, tmp_path: Path) -> None:
        done = subprocess.CompletedProcess([], 0, "a.b\n", "")
        with (
            patch(f"{MOD}.build_tool", return_value=tmp_path / "aapt2"),
            patch(f"{MOD}.subprocess.run", return_value=done) as runner,
        ):
            assert hook._apk_packages("adb install -r app.apk other.txt") == {
                "app.apk": "a.b"
            }
        assert runner.call_args.args[0][0] == str(tmp_path / "aapt2")

    def test_failures_leave_the_apk_unknown(self, tmp_path: Path) -> None:
        with patch(f"{MOD}.build_tool", return_value=tmp_path / "aapt2"):
            with patch(f"{MOD}.subprocess.run", side_effect=OSError("gone")):
                assert hook._apk_packages("adb install a.apk") == {}
            failed = subprocess.CompletedProcess([], 1, "", "bad apk")
            with patch(f"{MOD}.subprocess.run", return_value=failed):
                assert hook._apk_packages("adb install a.apk") == {}

    def test_no_sdk_means_no_lookup(self) -> None:
        with patch(f"{MOD}.build_tool", side_effect=UiAutomationError("no sdk")):
            assert hook._apk_packages("adb install a.apk") == {}

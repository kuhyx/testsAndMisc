"""Tests for :mod:`python_pkg.android_ui._mcp_target` and the server entry point.

Device selection must never guess: with several devices and no serial the
call fails, naming every serial, before any driver exists.
"""

from __future__ import annotations

import runpy
import subprocess
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from fastmcp.exceptions import ToolError
import pytest

from python_pkg.android_ui import _mcp_target
from python_pkg.phone_lease import NoPhoneError

if TYPE_CHECKING:
    from collections.abc import Iterator

TARGET = "python_pkg.android_ui._mcp_target"
DEVICES = (
    "List of devices attached\n"
    "23181JEGR08034\tdevice\n"
    "emulator-5554\tdevice\n"
    "OFFLINE1\toffline\n"
    "\n"
)


def _adb_devices(stdout: str) -> MagicMock:
    return MagicMock(return_value=subprocess.CompletedProcess([], 0, stdout, ""))


@pytest.fixture(autouse=True)
def _adb_on_path() -> Iterator[None]:
    with patch(f"{TARGET}.shutil.which", return_value="/usr/bin/adb"):
        yield


class TestAttachedSerials:
    def test_lists_only_ready_devices(self) -> None:
        with patch(f"{TARGET}.subprocess.run", _adb_devices(DEVICES)):
            assert _mcp_target.attached_serials() == [
                "23181JEGR08034",
                "emulator-5554",
            ]

    def test_adb_that_cannot_run_means_no_devices(self) -> None:
        with patch(f"{TARGET}.subprocess.run", side_effect=OSError("no adb")):
            assert _mcp_target.attached_serials() == []

    def test_adb_not_installed_means_no_devices(self) -> None:
        with (
            patch(f"{TARGET}.shutil.which", return_value=None),
            patch(f"{TARGET}.subprocess.run") as run,
        ):
            assert _mcp_target.attached_serials() == []
        run.assert_not_called()


class TestResolve:
    def test_two_devices_and_no_serial_lists_both(self) -> None:
        with (
            patch(f"{TARGET}.resolve_serial", side_effect=NoPhoneError("several")),
            patch(f"{TARGET}.subprocess.run", _adb_devices(DEVICES)),
            patch(f"{TARGET}.AndroidUi") as driver,
            pytest.raises(ToolError) as caught,
        ):
            _mcp_target.connect(None, "0", "tap")
        assert "23181JEGR08034" in str(caught.value)
        assert "emulator-5554" in str(caught.value)
        driver.assert_not_called()

    def test_no_device_keeps_the_lease_message(self) -> None:
        with (
            patch(f"{TARGET}.resolve_serial", side_effect=NoPhoneError("no phone")),
            patch(f"{TARGET}.subprocess.run", _adb_devices("List\n")),
            pytest.raises(ToolError, match="no phone"),
        ):
            _mcp_target.connect(None, "0", "tap")

    def test_explicit_serial_drives_that_device(self) -> None:
        with (
            patch(f"{TARGET}.acquire") as acquire,
            patch(f"{TARGET}.AndroidUi") as driver,
        ):
            _mcp_target.connect("emulator-5554", 0, "dump")
        assert acquire.call_args.args[0] == "emulator-5554"
        driver.assert_called_once_with(serial="emulator-5554", display=None)

    def test_bad_display_is_a_tool_error(self) -> None:
        with (
            patch(f"{TARGET}.resolve_serial", return_value="SER1"),
            patch("python_pkg.android_ui.cli.own_display", return_value=None),
            patch("python_pkg.android_ui.cli.owner_id", return_value="claude:1"),
            pytest.raises(ToolError, match="display id or 'self'"),
        ):
            _mcp_target.connect(None, "main", "dump")


class TestRedact:
    def test_empty_text_leaves_the_message_alone(self) -> None:
        assert _mcp_target.redact("no element", "") == "no element"

    def test_text_outside_the_adb_command_is_still_removed(self) -> None:
        assert "s3cr3t" not in _mcp_target.redact("stderr: s3cr3t", "s3cr3t")


class TestEntryPoint:
    def test_main_runs_stdio(self) -> None:
        sys.modules.pop("python_pkg.android_ui.mcp_server", None)
        with patch("fastmcp.FastMCP.run") as run:
            runpy.run_module("python_pkg.android_ui.mcp_server", run_name="__main__")
        run.assert_called_once_with(transport="stdio", show_banner=False)

"""The CLI wrapper: exit codes and the one-line outputs."""

from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from python_pkg.phone_lease import __main__ as cli
from python_pkg.phone_lease import _cleanup
from python_pkg.phone_lease import lease as lease_mod

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def lease_dir(tmp_path: Path) -> Iterator[None]:
    with patch.object(lease_mod, "LEASE_DIR", tmp_path / "leases"):
        yield


def test_acquire_then_status_then_release(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["acquire", "PIXEL", "--note", "deploy"]) == 0
    assert "held by" in capsys.readouterr().out
    assert cli.main(["status", "PIXEL"]) == 0
    assert "(deploy)" in capsys.readouterr().out
    assert cli.main(["release", "PIXEL"]) == 0
    assert capsys.readouterr().out == "released\n"
    assert cli.main(["status", "PIXEL"]) == 0
    assert capsys.readouterr().out == "free\n"


def test_release_without_holding(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["release", "PIXEL"]) == 1
    assert "not held by" in capsys.readouterr().out


def test_foreign_holder_exits_3(capsys: pytest.CaptureFixture[str]) -> None:
    lease_mod.acquire(
        "PIXEL", "manga", owner="someone-else", terms=lease_mod.Terms(ttl=1000)
    )
    assert cli.main(["acquire", "PIXEL", "--wait", "0"]) == 3
    assert "held by someone-else (manga)" in capsys.readouterr().err


def test_module_entry_point() -> None:
    # runpy warns if __main__ is already imported (this file imports it), so
    # drop it first; the test then runs the real module top to bottom.
    sys.modules.pop("python_pkg.phone_lease.__main__", None)
    with (
        patch("sys.argv", ["phone-lease", "status", "PIXEL"]),
        pytest.raises(SystemExit) as excinfo,
    ):
        runpy.run_module("python_pkg.phone_lease", run_name="__main__")
    assert excinfo.value.code == 0


def test_package_scopes_coexist_and_holds(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.dict("os.environ", {"PHONE_LEASE_OWNER": "me"}):
        assert cli.main(["acquire", "PIXEL", "--package", "a.b"]) == 0
        assert "[pkg:a.b]" in capsys.readouterr().out
        assert cli.main(["holds", "PIXEL", "--package", "a.b"]) == 0
        assert cli.main(["holds", "PIXEL", "--package", "c.d"]) == 1
        assert cli.main(["holds", "PIXEL", "--package", "a.b", "--owner", "x"]) == 1
        assert cli.main(["release", "PIXEL", "--package", "a.b"]) == 0


def test_whole_phone_with_cleanup(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(_cleanup, "spawn_reaper") as spawn,
        patch.object(_cleanup, "run") as run,
    ):
        argv = ["acquire", "PIXEL", "--whole-phone", "--cleanup", "adb x", "--ttl", "9"]
        assert cli.main(argv) == 0
        spawn.assert_called_once()
        assert cli.main(["release", "PIXEL", "--whole-phone"]) == 0
        run.assert_called_once_with(("adb x",))
    assert "[whole-phone]" in capsys.readouterr().out


def test_status_json_and_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["status", "PIXEL", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    lease_mod.acquire("PIXEL", "n", owner="o")
    assert cli.main(["status", "PIXEL", "--json"]) == 0
    (only,) = json.loads(capsys.readouterr().out)
    assert (only["owner"], only["scope"]) == ("o", "pkg:__screen__")


def test_whoami(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.dict("os.environ", {"PHONE_LEASE_OWNER": "claude:42"}):
        assert cli.main(["whoami"]) == 0
    assert capsys.readouterr().out == "claude:42\n"


def test_reap_subcommand_delegates() -> None:
    with patch.object(cli, "reap") as reap:
        assert cli.main(["reap", "S", "--owner", "o", "--scope", "whole-phone"]) == 0
    reap.assert_called_once_with("S", "o", "whole-phone")


def test_serial_resolved_or_exit_4(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.dict("os.environ", {"ANDROID_SERIAL": "ENVPHONE"}):
        assert cli.main(["status"]) == 0
    assert capsys.readouterr().out == "free\n"
    with (
        patch.dict("os.environ", {"ANDROID_SERIAL": "", "ADB_SERIAL": ""}),
        patch("python_pkg.phone_lease.serial._adb_serial", return_value=""),
    ):
        assert cli.main(["status"]) == 4
    assert "no phone serial" in capsys.readouterr().err

"""The CLI wrapper: exit codes and the one-line outputs."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from python_pkg.phone_lease import __main__ as cli
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
    lease_mod.acquire("PIXEL", "manga", owner="someone-else", ttl=1000)
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

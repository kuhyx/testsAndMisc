"""Which lease owners count as dead: only sessions whose process is gone."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.phone_lease.owner import owner_alive

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def proc(tmp_path: Path) -> Path:
    for pid, comm in ((10, "claude"), (11, "zsh"), (12, "bash")):
        (tmp_path / str(pid)).mkdir()
        (tmp_path / str(pid) / "comm").write_text(f"{comm}\n")
    return tmp_path


@pytest.mark.parametrize(
    ("owner", "alive"),
    [
        ("claude:10", True),
        ("claude:11", False),  # pid reused by another program
        ("claude:99", False),  # gone
        ("phone_deploy:12", True),
        ("phone_deploy:99", False),
        ("pid:99", True),  # the CLI's own pid: dead right after acquire
        ("ci-run-7", True),
        ("claude:abc", True),
    ],
)
def test_owner_alive(proc: Path, owner: str, *, alive: bool) -> None:
    assert owner_alive(owner, proc_root=proc) is alive

"""Reading phone_vd.sh's per-session state."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

import pytest

from python_pkg.phone_guard import vd_state
from python_pkg.phone_guard.tests.conftest import make_display


def test_default_root_is_under_the_runtime_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("PHONE_VD_STATE_DIR")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert vd_state.state_root() == tmp_path / "phone_vd"


def test_tmpdir_never_moves_the_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("PHONE_VD_STATE_DIR")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    roots = set()
    for tmpdir in ("/var/disktmp", str(tmp_path / "other")):
        monkeypatch.setenv("TMPDIR", tmpdir)
        monkeypatch.setattr(tempfile, "tempdir", None)
        roots.add(vd_state.state_root())
    assert roots == {tmp_path / "phone_vd"}


def test_state_dir_env_wins_over_runtime_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("PHONE_VD_STATE_DIR", str(tmp_path / "override"))
    assert vd_state.state_root() == tmp_path / "override"


def test_missing_runtime_dir_falls_back_to_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("PHONE_VD_STATE_DIR")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "absent"))
    assert vd_state.state_root() == Path("/", "tmp", "phone_vd")


def test_unset_runtime_dir_uses_run_user_uid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PHONE_VD_STATE_DIR")
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setattr(Path, "is_dir", lambda self: str(self) == "/run/user/4242")
    monkeypatch.setattr(os, "getuid", lambda: 4242)
    assert vd_state.state_root() == Path("/run/user/4242/phone_vd")


def test_owner_dir_name_matches_the_script() -> None:
    assert vd_state.owner_dir_name("claude:123") == "claude_123"


def test_lists_and_finds_displays(isolated_state: Path) -> None:
    make_display(isolated_state, "S", "claude_1", "9", "a.b")
    make_display(isolated_state, "S", "claude_2", "10", "c.d")
    make_display(isolated_state, "S", "claude_3", "gone", "e.f")
    assert [d.display for d in vd_state.displays("S")] == [9, 10]
    mine = vd_state.own_display("S", "claude:1")
    assert mine is not None
    assert (mine.display, mine.package, mine.sf) == (9, "a.b", "123")
    assert vd_state.own_display("S", "claude:9") is None
    other = vd_state.display_owner("S", 10)
    assert other is not None
    assert other.owner_dir == "claude_2"
    assert vd_state.display_owner("S", 11) is None


def test_no_state_means_no_displays() -> None:
    assert vd_state.displays("NOPE") == []


def test_unreadable_files_read_as_empty(isolated_state: Path) -> None:
    make_display(isolated_state, "S", "claude_1", "9", "a.b")
    (isolated_state / "phone_vd" / "S" / "claude_1" / "package").unlink()
    (isolated_state / "phone_vd" / "S" / "claude_1" / "package").mkdir()
    assert vd_state.displays("S")[0].package == ""

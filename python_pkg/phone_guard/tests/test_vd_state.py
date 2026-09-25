"""Reading phone_vd.sh's per-session state."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.phone_guard import vd_state
from python_pkg.phone_guard.tests.conftest import make_display


def test_default_root_is_under_the_temp_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHONE_VD_STATE_DIR")
    assert vd_state.state_root().name == "phone_vd"


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

"""Tests for the around-a-verdict chores and for undo finding moved keeps."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_pkg.wsg_grabber import housekeeping, paths
from python_pkg.wsg_grabber.models import Verdict
from python_pkg.wsg_grabber.tests.conftest import item, reviewed

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def prune_calls(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Replace the prune with a recorder.

    Args:
        monkeypatch: Patching helper.

    Returns:
        list[object]: One entry per prune call.
    """
    calls: list[object] = []
    monkeypatch.setattr(
        housekeeping,
        "prune_trash",
        calls.append,
    )
    return calls


def test_startup_migrates_then_prunes(
    monkeypatch: pytest.MonkeyPatch,
    prune_calls: list[object],
) -> None:
    order: list[str] = []
    monkeypatch.setattr(
        housekeeping,
        "migrate_keep",
        lambda _conn: order.append("migrate"),
    )
    housekeeping.on_startup("conn")
    assert order == ["migrate"]
    assert prune_calls == ["conn"]


@pytest.mark.parametrize(
    ("choice", "expected"),
    [(Verdict.SKIP, ["conn"]), (Verdict.KEEP, [])],
)
def test_only_a_pass_triggers_a_prune(
    prune_calls: list[object],
    choice: Verdict,
    expected: list[object],
) -> None:
    housekeeping.after_verdict("conn", choice)
    assert prune_calls == expected


def test_a_pass_is_located_in_trash() -> None:
    action = reviewed(item(), Verdict.SKIP)
    assert housekeeping.locate_reviewed(action) == paths.trash_dir() / "a.webm"


@pytest.mark.parametrize(
    "place",
    [
        paths.keep_dir,
        lambda: paths.cloud_keep_dir(2001),
        paths.legacy_keep_dir,
        paths.downloads_dir,
        lambda: paths.cloud_root() / "Media" / "2001" / "03",
    ],
)
def test_a_keep_is_found_wherever_it_ended_up(place: Callable[[], Path]) -> None:
    paths.cloud_root().mkdir(parents=True)
    directory = place()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "a.webm").write_bytes(b"v")

    action = reviewed(item(), Verdict.KEEP)
    assert housekeeping.locate_reviewed(action) == directory / "a.webm"


def test_a_keep_that_is_nowhere_points_at_the_current_keep_dir() -> None:
    action = reviewed(item(), Verdict.KEEP)
    assert housekeeping.locate_reviewed(action) == paths.keep_dir() / "a.webm"

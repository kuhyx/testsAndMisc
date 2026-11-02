"""Tests for ``AndroidUi.scroll_to``: find a widget outside the viewport."""

from __future__ import annotations

import pytest

from python_pkg.android_ui import driver as drv
from python_pkg.android_ui._elements import (
    AmbiguousElementError,
    ElementNotFoundError,
)
from python_pkg.android_ui.tests.conftest import FakeDevice
from python_pkg.android_ui.tests.conftest import node as _node
from python_pkg.android_ui.tests.conftest import tree as _tree

MOD = "python_pkg.android_ui.driver"
_SCREEN = "[0,0][1080,2400]"


def _screen(*labels: str) -> str:
    """A screen of five filler rows (so the dump is not 'partial') plus labels."""
    rows = [_node("Window", bounds=_SCREEN)]
    rows += [_node(f"row{i}", bounds="[0,100][1080,200]") for i in range(4)]
    rows += [_node(label, bounds="[0,1000][1080,1100]") for label in labels]
    return _tree(*rows)


def _driver(
    monkeypatch: pytest.MonkeyPatch, trees: list[str]
) -> tuple[drv.AndroidUi, FakeDevice]:
    device = FakeDevice(trees)
    instance = drv.AndroidUi(settle_seconds=0.0)
    monkeypatch.setattr(instance, "_run", device.run)
    monkeypatch.setattr(f"{MOD}.time.sleep", lambda _s: None)
    return instance, device


def _swipes(device: FakeDevice) -> list[tuple[str, ...]]:
    return [c for c in device.calls if c[4:5] == ("swipe",)]


def test_visible_element_needs_no_swipe(monkeypatch: pytest.MonkeyPatch) -> None:
    ui, device = _driver(monkeypatch, [_screen("Backup")])
    assert ui.scroll_to("Backup").label == "Backup"
    assert _swipes(device) == []


def test_swipes_up_until_the_element_appears(monkeypatch: pytest.MonkeyPatch) -> None:
    ui, device = _driver(
        monkeypatch, [_screen("A"), _screen("B"), _screen("B", "Backup")]
    )
    assert ui.scroll_to("Backup").label == "Backup"
    swipes = _swipes(device)
    assert len(swipes) == 2
    # finger travels upward through the middle of the screen
    x1, y1, x2, y2 = (int(v) for v in swipes[0][5:9])
    assert x1 == x2 == 540
    assert y1 > y2
    assert 0 < y2 < y1 < 2400


def test_stops_at_the_end_of_the_list(monkeypatch: pytest.MonkeyPatch) -> None:
    # The screen stops changing once the list bottoms out: say so, don't spin.
    ui, device = _driver(monkeypatch, [_screen("A")])
    with pytest.raises(ElementNotFoundError, match="Backup"):
        ui.scroll_to("Backup", max_swipes=10)
    assert len(_swipes(device)) == 1


def test_gives_up_after_max_swipes(monkeypatch: pytest.MonkeyPatch) -> None:
    trees = [_screen(f"item{i}") for i in range(10)]
    ui, device = _driver(monkeypatch, trees)
    with pytest.raises(ElementNotFoundError, match="Backup"):
        ui.scroll_to("Backup", max_swipes=3)
    assert len(_swipes(device)) == 3


def test_ambiguity_is_still_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    ui, _ = _driver(monkeypatch, [_screen("Backup now", "Backup later")])
    with pytest.raises(AmbiguousElementError):
        ui.scroll_to("Backup")


def test_the_last_allowed_swipe_may_reveal_it(monkeypatch: pytest.MonkeyPatch) -> None:
    ui, _ = _driver(monkeypatch, [_screen("A"), _screen("Backup")])
    assert ui.scroll_to("Backup", max_swipes=1).label == "Backup"

"""Tests for composing the root image and handing it to feh."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from PIL import Image
import pytest

from python_pkg.wallpaper_rotator import _paint, _palette

if TYPE_CHECKING:
    from pathlib import Path


def test_layout_keeps_only_active_outputs() -> None:
    outputs = [
        {
            "name": "DP-0",
            "active": True,
            "rect": {"x": 0, "y": 5, "width": 4, "height": 3},
        },
        {
            "name": "HDMI-0",
            "active": False,
            "rect": {"x": 9, "y": 9, "width": 9, "height": 9},
        },
    ]
    assert _paint.layout(outputs) == {"DP-0": (0, 5, 4, 3)}


def test_compose_places_each_image_and_skips_missing_ones() -> None:
    rects = {"A": (0, 0, 2, 2), "B": (2, 0, 2, 2), "C": (0, 2, 4, 1)}
    images = {
        "A": Image.new("RGB", (2, 2), (255, 0, 0)),
        "B": Image.new("RGB", (2, 2), (0, 255, 0)),
    }
    root = _paint.compose(rects, images)
    assert root.size == (4, 3)
    assert root.getpixel((0, 0)) == (255, 0, 0)
    assert root.getpixel((3, 1)) == (0, 255, 0)
    assert root.getpixel((0, 2)) == _palette.DEEP


def test_compose_without_outputs_is_one_pixel() -> None:
    assert _paint.compose({}, {}).size == (1, 1)


def test_apply_saves_image_and_runs_feh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> None:
        calls.append(cmd)
        assert kwargs == {"check": True}

    monkeypatch.setattr(subprocess, "run", fake_run)
    target = tmp_path / "cache" / "root.png"
    _paint.apply(Image.new("RGB", (3, 2)), target)
    with Image.open(target) as saved:
        assert saved.size == (3, 2)
    assert calls == [
        ["/usr/bin/feh", "--no-fehbg", "--no-xinerama", "--bg-tile", str(target)]
    ]

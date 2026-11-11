"""Compose per-monitor images into one root image and hand it to feh."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, cast

from PIL import Image

from python_pkg.wallpaper_rotator import _palette

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

Rect = tuple[int, int, int, int]


def layout(outputs: Sequence[Mapping[str, object]]) -> dict[str, Rect]:
    """Map each active output from ``i3-msg -t get_outputs`` to (x, y, w, h)."""
    rects: dict[str, Rect] = {}
    for output in outputs:
        if not output.get("active"):
            continue
        rect = cast("Mapping[str, int]", output["rect"])
        rects[str(output["name"])] = (
            rect["x"],
            rect["y"],
            rect["width"],
            rect["height"],
        )
    return rects


def compose(
    rects: Mapping[str, Rect], images: Mapping[str, Image.Image]
) -> Image.Image:
    """Paste each output's image at its position on one root-sized canvas."""
    width = max((x + w for x, _, w, _ in rects.values()), default=1)
    height = max((y + h for _, y, _, h in rects.values()), default=1)
    root = Image.new("RGB", (width, height), _palette.DEEP)
    for name, (x, y, _, _) in rects.items():
        if name in images:
            root.paste(images[name], (x, y))
    return root


def apply(root: Image.Image, target: Path) -> None:
    """Write the root image and set it as the X background with feh.

    One image spanning the whole root avoids relying on feh's Xinerama
    screen order matching i3's output names.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    root.save(target, compress_level=1)
    subprocess.run(
        ["/usr/bin/feh", "--no-fehbg", "--no-xinerama", "--bg-tile", str(target)],
        check=True,
    )

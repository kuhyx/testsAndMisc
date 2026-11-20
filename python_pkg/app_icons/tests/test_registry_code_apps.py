"""Tests for the kartka, leetcode and todoimpl registry entries.

Those three apps shipped family icons before they were registered here; the
glyphs are ports of the shipped ``icon_foreground.svg`` fragments, so these
tests render each one through the real pipeline into ``tmp_path`` (never the
app's own repo) and check the standard-size set comes out.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from PIL import Image
import pytest

from python_pkg.app_icons import apps, generate, glyphs, labels, style

if TYPE_CHECKING:
    from pathlib import Path

# key -> (glyph, icon_name, linux, repo path under ~)
_EXPECTED: dict[str, tuple[str, str, bool, str]] = {
    "kartka": ("document-split", "kartka", True, "src/kartka"),
    "leetcode": ("code-brackets", "leetcode-guard-app", True, "src/leetcode-guard/app"),
    "todoimpl": ("screen-tick-play", "todoimpl", False, "src/todoImplementer/app"),
    "logo_review": ("square-tick", "logo-review", False, "src/logo-review/app"),
}


@pytest.mark.parametrize("key", sorted(_EXPECTED))
class TestCodeAppEntries:
    def test_entry_matches_disk_facts(self, key: str) -> None:
        glyph, icon_name, linux, repo = _EXPECTED[key]
        app = apps.get_app(key)
        assert app.glyph == glyph
        assert app.icon_name == icon_name
        assert app.linux is linux
        assert app.repo == apps.Path.home() / repo
        assert glyphs.get_glyph(glyph).name == glyph

    def test_label_is_valid(self, key: str) -> None:
        assert labels.label_problems(apps.get_app(key).label) == []

    def test_renders_standard_size_set(self, key: str, tmp_path: Path) -> None:
        app = dataclasses.replace(apps.get_app(key), repo=tmp_path / key)
        written = generate.write_assets(app)
        assert sorted(path.name for path in written) == sorted(
            f"{stem}.{ext}"
            for stem in ("icon", "icon_foreground", "icon_monochrome")
            for ext in ("svg", "png")
        )
        for path in written:
            if path.suffix == ".png":
                with Image.open(path) as image:
                    assert image.size == (style.CANVAS, style.CANVAS)


@pytest.mark.parametrize("key", ["kartka", "leetcode"])
def test_renders_linux_set(key: str, tmp_path: Path) -> None:
    icons = generate.write_linux_icons(apps.get_app(key), tmp_path)
    assert len(icons) == len(style.LINUX_ICON_SIZES)
    for size, path in zip(style.LINUX_ICON_SIZES, icons, strict=True):
        with Image.open(path) as image:
            assert image.size == (size, size)


def test_filled_parts_take_the_accent_marker() -> None:
    """Folded corner and play triangle recolour on the monochrome layer."""
    for name in ("document-split", "screen-tick-play"):
        assert f'fill="{style.ACCENT_MARKER}"' in glyphs.get_glyph(name).body

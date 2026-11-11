"""Every style renders the exact output size and stays dark."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image
import pytest

from python_pkg.wallpaper_rotator._context import RenderContext
from python_pkg.wallpaper_rotator.styles import STYLES

if TYPE_CHECKING:
    from pathlib import Path

# Mean brightness ceiling (0-255): the whole point is "not blinding".
_DARK_MEAN = 80


@pytest.fixture
def ctx(tmp_path: Path) -> RenderContext:
    earth = tmp_path / "earth"
    earth.mkdir()
    Image.new("RGB", (64, 32), (40, 90, 160)).save(earth / "day.jpg")
    Image.new("RGB", (64, 32), (5, 5, 10)).save(earth / "night.jpg")
    conf = tmp_path / "shutdown.conf"
    conf.write_text("MON_WED_MINUTES=1380\nTHU_SUN_MINUTES=1380\n")
    return RenderContext(
        now=datetime(2026, 11, 11, 21, 30, tzinfo=UTC),
        data_home=tmp_path / "share",
        earth_dir=earth,
        shutdown_conf=conf,
    )


def test_all_six_styles_registered() -> None:
    assert len(STYLES) == 6


@pytest.mark.parametrize("name", sorted(STYLES))
@pytest.mark.parametrize("size", [(384, 216), (256, 144)])
def test_style_is_exact_size_and_dark(
    name: str, size: tuple[int, int], ctx: RenderContext
) -> None:
    image = STYLES[name].render(ctx, size, np.random.default_rng(3))
    assert image.size == size
    assert image.mode == "RGB"
    assert float(np.asarray(image).mean()) < _DARK_MEAN

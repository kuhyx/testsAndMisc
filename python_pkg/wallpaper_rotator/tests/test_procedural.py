"""Both procedural generators are reachable and render the requested size."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from python_pkg.wallpaper_rotator import _style_procedural as _procedural
from python_pkg.wallpaper_rotator._context import RenderContext

_SIZE = (320, 180)


def _seed_choosing(generator: str) -> int:
    """First seed whose first draw makes ``render`` pick the wanted generator."""
    return next(
        seed
        for seed in range(100)
        if (np.random.default_rng(seed).random() < _procedural._FLOW_SHARE)
        == (generator == "flow")
    )


@pytest.mark.parametrize("generator", ["flow", "voronoi"])
def test_render_reaches_each_generator(generator: str) -> None:
    ctx = RenderContext(
        now=datetime(2026, 11, 11, tzinfo=UTC),
        data_home=Path(),
        earth_dir=Path(),
        shutdown_conf=Path(),
    )
    rng = np.random.default_rng(_seed_choosing(generator))
    expected = getattr(_procedural, f"_{generator}")(
        _SIZE, np.random.default_rng(_seed_choosing(generator))
    )
    assert _procedural.render(ctx, _SIZE, rng).size == expected.size == _SIZE

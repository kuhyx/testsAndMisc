"""The six background styles, keyed by name."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from python_pkg.wallpaper_rotator import _style_clock as _clock
from python_pkg.wallpaper_rotator import _style_earth as _earth
from python_pkg.wallpaper_rotator import _style_gradient as _gradient
from python_pkg.wallpaper_rotator import _style_heatmap as _heatmap
from python_pkg.wallpaper_rotator import _style_plasma as _plasma
from python_pkg.wallpaper_rotator import _style_procedural as _procedural

if TYPE_CHECKING:
    import numpy as np
    from PIL import Image

    from python_pkg.wallpaper_rotator._context import RenderContext

RenderFn = Callable[
    ["RenderContext", tuple[int, int], "np.random.Generator"], "Image.Image"
]


def _always(_ctx: RenderContext) -> bool:
    return True


@dataclass(frozen=True)
class Style:
    """A renderer plus a check that its inputs exist."""

    render: RenderFn
    available: Callable[[RenderContext], bool] = _always


STYLES: dict[str, Style] = {
    "gradient": Style(_gradient.render),
    "procedural": Style(_procedural.render),
    "heatmap": Style(_heatmap.render),
    "clock": Style(_clock.render),
    "earth": Style(_earth.render, _earth.available),
    "plasma": Style(_plasma.render),
}

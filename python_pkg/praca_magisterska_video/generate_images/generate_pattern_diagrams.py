#!/usr/bin/env python3
"""Generate pattern cataloguing diagrams for PYTANIE 14 (AIS).

  1. Pattern Template Structure — the standard fields every pattern has
  2. Catalog Classification Map — catalogs arranged by scope & domain
  3. Pattern Language Network — how patterns reference each other.

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")
from pathlib import Path

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)

DPI = 300
BG = "white"
LN = "black"
FS = 9
FS_TITLE = 13
FS_SMALL = 7.5
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"

_BAND_HEIGHTS = [0.7, 1.3, 1.4, 1.5, 1.5]


def draw_box(
    ax: Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    fill: str = "white",
    lw: float = 1.2,
    fontsize: float = FS,
    fontweight: str = "normal",
    ha: str = "center",
    va: str = "center",
    rounded: bool = True,
) -> None:
    """Draw a labeled box on the axes."""
    if rounded:
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.08",
            lw=lw,
            edgecolor=LN,
            facecolor=fill,
        )
    else:
        rect = mpatches.Rectangle((x, y), w, h, lw=lw, edgecolor=LN, facecolor=fill)
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha=ha,
        va=va,
        fontsize=fontsize,
        fontweight=fontweight,
        wrap=True,
    )


def draw_arrow(
    ax: Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    lw: float = 1.2,
    style: str = "->",
    color: str = LN,
) -> None:
    """Draw an arrow between two points."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": style, "color": color, "lw": lw},
    )


# ============================================================
# 1. Pattern Template Structure (NaPSiRoKo mnemonic)
# ============================================================


if __name__ == "__main__":
    from python_pkg.praca_magisterska_video.generate_images._pattern_navigation import (
        generate_pattern_language_navigation,
    )
    from python_pkg.praca_magisterska_video.generate_images._pattern_pillars_observer import (
        generate_observer_card_filled,
        generate_three_pillars,
    )
    from python_pkg.praca_magisterska_video.generate_images._pattern_template_catalog import (
        generate_catalog_map,
        generate_pattern_template,
    )

    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating pattern diagrams...")
    generate_pattern_template()
    generate_catalog_map()
    generate_three_pillars()
    generate_observer_card_filled()
    generate_pattern_language_navigation()
    _logger.info("All pattern diagrams saved to %s/", OUTPUT_DIR)

"""Common constants and utilities for scheduling diagrams."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)

DPI = 300
BG = "white"
LN = "black"
FS = 8
FS_TITLE = 11
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"

MIN_COLUMN_INDEX = 3
FONTWEIGHT_THRESHOLD = 3


def draw_box(
    ax: Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    fill: str = "white",
    lw: float = 1.2,
    fontsize: float = FS,
    fontweight: str = "normal",
    ha: str = "center",
    va: str = "center",
    *,
    rounded: bool = True,
) -> None:
    """Draw box."""
    if rounded:
        rect = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.05", lw=lw, edgecolor=LN, facecolor=fill
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
    lw: float = 1.2,
    style: str = "->",
    color: str = LN,
) -> None:
    """Draw arrow."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": style, "color": color, "lw": lw},
    )

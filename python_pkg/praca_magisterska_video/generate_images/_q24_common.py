"""Common utilities and constants for Q24 diagram generation.

Monochrome, A4-printable PNGs (300 DPI).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

_logger = logging.getLogger(__name__)

rng = np.random.default_rng(42)

DPI = 300
BG = "white"
LN = "black"
FS = 8
FS_TITLE = 11
FS_SMALL = 6.5
FS_LABEL = 9
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"

_PIXEL_BRIGHT_THRESH = 127
_GRADIENT_BRIGHT_THRESH = 100
_DATA_BRIGHT_THRESH = 5
_II_BRIGHT_THRESH = 25
_DOTS_STAGE_IDX = 2


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
    edgecolor: str = LN,
    linestyle: str = "-",
) -> None:
    """Draw box."""
    if rounded:
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.05",
            lw=lw,
            edgecolor=edgecolor,
            facecolor=fill,
            linestyle=linestyle,
        )
    else:
        rect = mpatches.Rectangle(
            (x, y),
            w,
            h,
            lw=lw,
            edgecolor=edgecolor,
            facecolor=fill,
            linestyle=linestyle,
        )
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
    """Draw arrow."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": style, "color": color, "lw": lw},
    )


def save_fig(fig: Figure, name: str) -> None:
    """Save fig."""
    path = str(Path(OUTPUT_DIR) / name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG, pad_inches=0.15)
    plt.close(fig)
    _logger.info("  Saved: %s", path)


def draw_table(
    ax: Axes,
    headers: list[str],
    rows: list[list[str]],
    x0: float,
    y0: float,
    col_widths: list[float],
    *,
    row_h: float = 0.4,
    header_fill: str = GRAY2,
    row_fills: list[str] | None = None,
    fontsize: float = FS,
    header_fontsize: float | None = None,
) -> None:
    """Draw table."""
    if header_fontsize is None:
        header_fontsize = fontsize
    len(headers)
    cx = x0
    for j, hdr in enumerate(headers):
        draw_box(
            ax,
            cx,
            y0,
            col_widths[j],
            row_h,
            hdr,
            fill=header_fill,
            fontsize=header_fontsize,
            fontweight="bold",
            rounded=False,
        )
        cx += col_widths[j]
    for i, row in enumerate(rows):
        cy = y0 - (i + 1) * row_h
        cx = x0
        fill = GRAY4 if (i % 2 == 0) else "white"
        if row_fills and i < len(row_fills):
            fill = row_fills[i]
        for j, cell in enumerate(row):
            fw = "bold" if j == 0 else "normal"
            draw_box(
                ax,
                cx,
                cy,
                col_widths[j],
                row_h,
                cell,
                fill=fill,
                fontsize=fontsize,
                fontweight=fw,
                rounded=False,
            )
            cx += col_widths[j]

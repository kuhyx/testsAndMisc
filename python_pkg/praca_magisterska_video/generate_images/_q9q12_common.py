"""Common constants and drawing utilities for Q9/Q12 diagrams."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

mpl.use("Agg")
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import numpy as np

_logger = logging.getLogger(__name__)

DPI = 300
BG = "white"
LN = "black"
FS = 8
FS_TITLE = 11
FS_SMALL = 6.5
FS_EDGE = 9
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"
LIGHT_GREEN = "#D5E8D4"
LIGHT_RED = "#F8D7DA"
LIGHT_BLUE = "#D6EAF8"
LIGHT_YELLOW = "#FFF9C4"
LIGHT_ORANGE = "#FFE0B2"
_LAST_CONDITION_INDEX = 3
_CENTER_Y = 2.5


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
    edgecolor: str = LN,
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
        )
    else:
        rect = mpatches.Rectangle(
            (x, y), w, h, lw=lw, edgecolor=edgecolor, facecolor=fill
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


def draw_network_node(
    ax: Axes,
    name: str,
    pos: tuple[float, float],
    color: str = "white",
    fontsize: float = 10,
    r: float = 0.3,
) -> None:
    """Draw a network node (circle)."""
    x, y = pos
    circle = plt.Circle(
        (x, y), r, fill=True, facecolor=color, edgecolor=LN, linewidth=1.5, zorder=5
    )
    ax.add_patch(circle)
    ax.text(
        x,
        y,
        name,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        zorder=6,
    )


def draw_network_edge(
    ax: Axes,
    pos1: tuple[float, float],
    pos2: tuple[float, float],
    label: str = "",
    color: str = LN,
    lw: float = 1.5,
    offset: float = 0.0,
    *,
    directed: bool = True,
    r: float = 0.33,
    label_bg: str = "white",
) -> None:
    """Draw a directed edge with label."""
    x1, y1 = pos1
    x2, y2 = pos2
    dx, dy = x2 - x1, y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    if length == 0:
        return
    sx = x1 + r * dx / length
    sy = y1 + r * dy / length
    ex = x2 - r * dx / length
    ey = y2 - r * dy / length

    if directed:
        ax.annotate(
            "",
            xy=(ex, ey),
            xytext=(sx, sy),
            arrowprops={"arrowstyle": "->", "color": color, "lw": lw},
        )
    else:
        ax.plot([sx, ex], [sy, ey], color=color, linewidth=lw, zorder=2)

    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        perp_x = -dy / length * (0.2 + offset)
        perp_y = dx / length * (0.2 + offset)
        ax.text(
            mx + perp_x,
            my + perp_y,
            str(label),
            ha="center",
            va="center",
            fontsize=FS_EDGE,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.1",
                "facecolor": label_bg,
                "edgecolor": GRAY3,
                "alpha": 0.95,
            },
            zorder=4,
        )

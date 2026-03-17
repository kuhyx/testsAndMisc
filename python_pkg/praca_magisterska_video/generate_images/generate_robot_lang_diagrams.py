#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 16: Języki programowania robotów.

A4-compatible, B&W, 300 DPI, laser-printer-friendly.

Diagrams:
  1. T-R-M-S abstraction pyramid
  2. Vendor languages comparison chart
  3. Robot movement types (PTP, LIN, CIRC)
  4. Online vs Offline programming flowchart
  5. ROS architecture (pub/sub nodes)
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
FS = 8
FS_TITLE = 11
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"
WHITE = "white"


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
    """Draw a labeled box on the axes.

    Args:
        ax: Matplotlib axes to draw on.
        x: Left edge x-coordinate.
        y: Bottom edge y-coordinate.
        w: Box width.
        h: Box height.
        text: Label text inside the box.
        fill: Fill color.
        lw: Line width.
        fontsize: Font size for label.
        fontweight: Font weight for label.
        ha: Horizontal alignment.
        va: Vertical alignment.
        rounded: Whether to use rounded corners.
    """
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
    *,
    lw: float = 1.2,
    style: str = "->",
    color: str = LN,
) -> None:
    """Draw an arrow annotation.

    Args:
        ax: Matplotlib axes to draw on.
        x1: Start x-coordinate.
        y1: Start y-coordinate.
        x2: End x-coordinate.
        y2: End y-coordinate.
        lw: Line width.
        style: Arrow style.
        color: Arrow color.
    """
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": style, "color": color, "lw": lw},
    )


# ============================================================
# 1. T-R-M-S Abstraction Pyramid


if __name__ == "__main__":
    from python_pkg.praca_magisterska_video.generate_images._robot_movement_ros import (
        draw_movement_types,
        draw_online_offline,
    )
    from python_pkg.praca_magisterska_video.generate_images._robot_pyramid_vendor import (
        draw_trms_pyramid,
        draw_vendor_comparison,
    )
    from python_pkg.praca_magisterska_video.generate_images._robot_ros_rapid import (
        draw_rapid_structure,
        draw_ros_architecture,
    )

    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating robot language diagrams...")
    draw_trms_pyramid()
    draw_vendor_comparison()
    draw_movement_types()
    draw_online_offline()
    draw_ros_architecture()
    draw_rapid_structure()
    _logger.info("All robot language diagrams saved to %s/", OUTPUT_DIR)

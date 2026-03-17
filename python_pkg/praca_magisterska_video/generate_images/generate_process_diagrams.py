#!/usr/bin/env python3
"""Generate 4 process modeling diagrams (BPMN, UML Activity, EPC, Flowchart).

all representing the same process: "Obsluga reklamacji" (Complaint Handling).
Output: A4-compatible, black & white, laser-printer-friendly PNG files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

from matplotlib.patches import FancyBboxPatch, Polygon

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)

# --- Common settings ---
DPI = 300
BG_COLOR = "white"
LINE_COLOR = "black"
FONT_SIZE = 9
TITLE_SIZE = 14
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def draw_arrow(
    ax: Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> None:
    """Draw arrow."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": "->", "color": LINE_COLOR, "lw": 1.3},
    )


def draw_line(
    ax: Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> None:
    """Draw line."""
    ax.plot(
        [x1, x2],
        [y1, y2],
        color=LINE_COLOR,
        lw=1.3,
        solid_capstyle="round",
    )


def draw_rounded_rect(
    ax: Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    fill: str = "white",
    lw: float = 1.5,
    fontsize: float = FONT_SIZE,
) -> None:
    """Draw rounded rect."""
    rect = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.3",
        linewidth=lw,
        edgecolor=LINE_COLOR,
        facecolor=fill,
    )
    ax.add_patch(rect)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize)


def draw_diamond(
    ax: Axes,
    x: float,
    y: float,
    size: float,
    text: str = "",
    *,
    fill: str = "white",
    fontsize: float = 8,
) -> None:
    """Draw diamond."""
    s = size
    diamond = Polygon(
        [(x, y + s), (x + s, y), (x, y - s), (x - s, y)],
        closed=True,
        linewidth=1.5,
        edgecolor=LINE_COLOR,
        facecolor=fill,
    )
    ax.add_patch(diamond)
    if text:
        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold",
        )


# =========================================================================
# 1. BPMN 2.0 Diagram
# =========================================================================


if __name__ == "__main__":
    from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
        generate_bpmn,
        generate_uml_activity,
    )
    from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
        generate_epc,
        generate_flowchart,
    )

    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating process diagrams...")
    generate_bpmn()
    generate_uml_activity()
    generate_epc()
    generate_flowchart()
    _logger.info("All process diagrams saved to %s/", OUTPUT_DIR)

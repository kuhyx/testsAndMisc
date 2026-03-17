#!/usr/bin/env python3
"""Generate study diagrams for defense preparation.

  1. PYTANIE 12: Network optimization models (mnemonic overview)
  2. PYTANIE 21: Vector clock timeline
  3. PYTANIE 22: Linearizability vs Sequential consistency, Paxos flow
  4. PYTANIE 23: Segmentation types and over-segmentation
  5. PYTANIE 24: HOG pipeline, SVM margin, R-CNN vs YOLO architecture.

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
FS = 8
FS_TITLE = 12
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
GRAY5 = "#C0C0C0"


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


if __name__ == "__main__":
    from python_pkg.praca_magisterska_video.generate_images._study_consensus import (
        draw_linearizability_vs_sequential,
        draw_paxos_flow,
    )
    from python_pkg.praca_magisterska_video.generate_images._study_network import (
        draw_network_models,
        draw_vector_clock_timeline,
    )
    from python_pkg.praca_magisterska_video.generate_images._study_vision import (
        draw_fsd_ssd,
        draw_hog_pipeline,
        draw_rcnn_evolution,
        draw_segmentation_types,
    )

    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating study diagrams...")
    draw_network_models()
    draw_vector_clock_timeline()
    draw_linearizability_vs_sequential()
    draw_paxos_flow()
    draw_hog_pipeline()
    draw_rcnn_evolution()
    draw_segmentation_types()
    draw_fsd_ssd()
    _logger.info("All diagrams saved to %s/", OUTPUT_DIR)

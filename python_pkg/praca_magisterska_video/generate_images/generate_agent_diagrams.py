#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 15: Agent upostaciowiony w robotyce.

Diagrams:
  1. See-Think-Act cycle of an embodied agent
  2. 3T Architecture (Planner / Sequencer / Controller)
  3. Behavior Tree example (robot pick-and-place)
  4. BDI model flow

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

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


@dataclass(frozen=True)
class BoxStyle:
    """Optional styling for boxes."""

    fill: str = "white"
    lw: float = 1.2
    fontsize: float = FS
    fontweight: str = "normal"
    ha: str = "center"
    va: str = "center"
    rounded: bool = True


@dataclass(frozen=True)
class ArrowCfg:
    """Optional config for arrows."""

    lw: float = 1.2
    style: str = "->"
    color: str = LN
    label: str = ""
    label_offset: float = 0.12


@dataclass(frozen=True)
class DashedArrowCfg:
    """Optional config for dashed arrows."""

    lw: float = 1.0
    color: str = LN
    label: str = ""
    label_offset: float = 0.12


def draw_box(
    ax: Axes,
    pos: tuple[float, float],
    size: tuple[float, float],
    text: str,
    style: BoxStyle | None = None,
) -> None:
    """Draw box."""
    s = style or BoxStyle()
    x, y = pos
    w, h = size
    if s.rounded:
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.05",
            lw=s.lw,
            edgecolor=LN,
            facecolor=s.fill,
        )
    else:
        rect = mpatches.Rectangle(
            (x, y),
            w,
            h,
            lw=s.lw,
            edgecolor=LN,
            facecolor=s.fill,
        )
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha=s.ha,
        va=s.va,
        fontsize=s.fontsize,
        fontweight=s.fontweight,
        wrap=True,
    )


def draw_arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    cfg: ArrowCfg | None = None,
) -> None:
    """Draw arrow."""
    c = cfg or ArrowCfg()
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": c.style,
            "color": c.color,
            "lw": c.lw,
        },
    )
    if c.label:
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2 + c.label_offset
        ax.text(
            mx,
            my,
            c.label,
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=c.color,
        )


def draw_dashed_arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    cfg: DashedArrowCfg | None = None,
) -> None:
    """Draw dashed arrow."""
    c = cfg or DashedArrowCfg()
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "->",
            "color": c.color,
            "lw": c.lw,
            "linestyle": "dashed",
        },
    )
    if c.label:
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2 + c.label_offset
        ax.text(
            mx,
            my,
            c.label,
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=c.color,
        )


# --- DIAGRAM 1: See-Think-Act Cycle ---


if __name__ == "__main__":
    from python_pkg.praca_magisterska_video.generate_images._agent_cognitive import (
        draw_bdi_model,
        draw_behavior_tree,
    )
    from python_pkg.praca_magisterska_video.generate_images._agent_reactive import (
        draw_3t_architecture,
        draw_see_think_act,
    )

    logging.basicConfig(level=logging.INFO)
    logger.info("Generating agent diagrams...")
    draw_see_think_act()
    draw_3t_architecture()
    draw_behavior_tree()
    draw_bdi_model()
    logger.info("All agent diagrams saved to %s/", OUTPUT_DIR)

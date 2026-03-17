"""Shared constants, dataclasses, and drawing helpers for automata diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

DPI = 300
BG = "white"
LN = "black"
FS = 8
FS_TITLE = 11
FS_SMALL = 6.5
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

INNER_RATIO = 0.82
ARROW_OFFSET = 0.4
LOOP_RAD = 1.8
LOOP_OFFSET = 0.12
LOOP_LABEL_OFFSET = 0.35
MUTATION_SCALE = 12
HEAD_MARKER_FONTSIZE = 8


@dataclass(frozen=True)
class StateStyle:
    """Optional styling for automaton state circles."""

    accepting: bool = False
    initial: bool = False
    fillcolor: str = "white"
    fontsize: float = FS


@dataclass(frozen=True)
class ArrowStyle:
    """Optional styling for curved arrows."""

    connectionstyle: str = "arc3,rad=0.3"
    fontsize: float = FS_SMALL
    label_offset: tuple[float, float] = (0, 0)


@dataclass(frozen=True)
class LoopStyle:
    """Optional styling for self-loops."""

    direction: str = "top"
    fontsize: float = FS_SMALL


def draw_state_circle(
    ax: Axes,
    pos: tuple[float, float],
    r: float,
    label: str,
    style: StateStyle | None = None,
) -> None:
    """Draw an automaton state circle."""
    s = style or StateStyle()
    x, y = pos
    circle = plt.Circle(
        (x, y),
        r,
        fill=True,
        facecolor=s.fillcolor,
        edgecolor=LN,
        linewidth=1.5,
        zorder=3,
    )
    ax.add_patch(circle)
    if s.accepting:
        inner = plt.Circle(
            (x, y),
            r * INNER_RATIO,
            fill=False,
            edgecolor=LN,
            linewidth=1.2,
            zorder=3,
        )
        ax.add_patch(inner)
    if s.initial:
        ax.annotate(
            "",
            xy=(x - r, y),
            xytext=(x - r - ARROW_OFFSET, y),
            arrowprops={
                "arrowstyle": "->",
                "color": LN,
                "lw": 1.5,
            },
            zorder=4,
        )
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=s.fontsize,
        fontweight="bold",
        zorder=5,
    )


def draw_curved_arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    label: str,
    style: ArrowStyle | None = None,
) -> None:
    """Draw a curved arrow between points with label."""
    s = style or ArrowStyle()
    x1, y1 = start
    x2, y2 = end
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={
            "arrowstyle": "->",
            "color": LN,
            "lw": 1.2,
            "connectionstyle": s.connectionstyle,
        },
        zorder=2,
    )
    mx = (x1 + x2) / 2 + s.label_offset[0]
    my = (y1 + y2) / 2 + s.label_offset[1]
    ax.text(
        mx,
        my,
        label,
        ha="center",
        va="center",
        fontsize=s.fontsize,
        fontstyle="italic",
        zorder=5,
        bbox={
            "boxstyle": "round,pad=0.15",
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.9,
        },
    )


def draw_self_loop(
    ax: Axes,
    pos: tuple[float, float],
    r: float,
    label: str,
    style: LoopStyle | None = None,
) -> None:
    """Draw a self-loop on a state."""
    s = style or LoopStyle()
    x, y = pos
    if s.direction == "top":
        loop = mpatches.FancyArrowPatch(
            (x - LOOP_OFFSET, y + r),
            (x + LOOP_OFFSET, y + r),
            connectionstyle=f"arc3,rad=-{LOOP_RAD}",
            arrowstyle="->",
            mutation_scale=MUTATION_SCALE,
            lw=1.2,
            color=LN,
            zorder=2,
        )
        ax.add_patch(loop)
        ax.text(
            x,
            y + r + LOOP_LABEL_OFFSET,
            label,
            ha="center",
            va="center",
            fontsize=s.fontsize,
            fontstyle="italic",
            zorder=5,
        )
    elif s.direction == "bottom":
        loop = mpatches.FancyArrowPatch(
            (x - LOOP_OFFSET, y - r),
            (x + LOOP_OFFSET, y - r),
            connectionstyle=f"arc3,rad={LOOP_RAD}",
            arrowstyle="->",
            mutation_scale=MUTATION_SCALE,
            lw=1.2,
            color=LN,
            zorder=2,
        )
        ax.add_patch(loop)
        ax.text(
            x,
            y - r - LOOP_LABEL_OFFSET,
            label,
            ha="center",
            va="center",
            fontsize=s.fontsize,
            fontstyle="italic",
            zorder=5,
        )

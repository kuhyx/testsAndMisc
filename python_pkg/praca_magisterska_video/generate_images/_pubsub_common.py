"""Common drawing primitives and constants for Pub/Sub diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

DPI = 300
BG = "white"
LN = "black"
FS = 9
FS_TITLE = 13
FIG_W = 8.27  # A4 width in inches
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
    """Config for arrows."""

    lw: float = 1.2
    style: str = "->"
    color: str = LN
    label: str = ""
    label_offset: float = 0.15
    label_fs: float = 8


@dataclass(frozen=True)
class DashedCfg:
    """Config for dashed arrows."""

    lw: float = 1.0
    color: str = LN
    label: str = ""
    label_offset: float = 0.15
    label_fs: float = 8


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
            fontsize=c.label_fs,
            color=c.color,
        )


def draw_dashed_arrow(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    cfg: DashedCfg | None = None,
) -> None:
    """Draw dashed arrow."""
    c = cfg or DashedCfg()
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
            fontsize=c.label_fs,
            color=c.color,
        )


def draw_cross(
    ax: Axes,
    pos: tuple[float, float],
    size: float = 0.15,
    lw: float = 2.5,
    color: str = "black",
) -> None:
    """Draw cross."""
    x, y = pos
    ax.plot(
        [x - size, x + size],
        [y - size, y + size],
        color=color,
        lw=lw,
    )
    ax.plot(
        [x - size, x + size],
        [y + size, y - size],
        color=color,
        lw=lw,
    )


def draw_check(
    ax: Axes,
    pos: tuple[float, float],
    size: float = 0.15,
    lw: float = 2.5,
    color: str = "black",
) -> None:
    """Draw check."""
    x, y = pos
    ax.plot(
        [x - size, x - size * 0.2],
        [y, y - size * 0.7],
        color=color,
        lw=lw,
    )
    ax.plot(
        [x - size * 0.2, x + size],
        [y - size * 0.7, y + size * 0.5],
        color=color,
        lw=lw,
    )


def save(fig: plt.Figure, name: str) -> None:
    """Save."""
    plt.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / name),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close(fig)

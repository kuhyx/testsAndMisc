"""Common utilities and constants for Q23 diagram generation.

A4-compatible, monochrome-friendly (grays + one accent), 300 DPI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)

rng = np.random.default_rng(42)

DPI = 300
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# Color palette — monochrome-friendly
BLACK = "#000000"
WHITE = "#FFFFFF"
GRAY1 = "#F5F5F5"
GRAY2 = "#E0E0E0"
GRAY3 = "#BDBDBD"
GRAY4 = "#9E9E9E"
GRAY5 = "#757575"
GRAY6 = "#424242"
ACCENT = "#4A90D9"  # single blue accent for highlights
ACCENT_LIGHT = "#B3D4FC"
RED_ACCENT = "#D32F2F"
GREEN_ACCENT = "#388E3C"

FS = 9
FS_TITLE = 11
FS_SMALL = 7
FS_TINY = 6

_RIDGE_X = 5
_VALLEY2_END = 9
_DARK_PIXEL_THRESHOLD = 100
_GRID_LAST_IDX = 3
_HIGHLIGHT_START = 3
_HIGHLIGHT_END = 5
_BRIGHT_THRESHOLD = 170
_OTSU_THRESHOLD = 128


def _save_figure(name: str) -> None:
    """Save current figure and log."""
    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / name),
        dpi=DPI,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()
    _logger.info("  ✓ %s", name)


def _render_text_lines(
    ax: Axes,
    lines: list[tuple[str, int, str, str]],
    *,
    x_pos: float = 0.5,
    start_y: float,
    y_step: float = 0.5,
    y_empty_step: float = 0.2,
) -> None:
    """Render a list of styled text lines on an axis."""
    y = start_y
    for txt, size, color, weight in lines:
        if txt == "":
            y -= y_empty_step
            continue
        ax.text(
            x_pos,
            y,
            txt,
            fontsize=size,
            color=color,
            fontweight=weight,
            va="top",
        )
        y -= y_step

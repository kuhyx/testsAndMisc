#!/usr/bin/env python3
"""Generate B&W normalization step diagrams for PYTANIE 3.

Each diagram shows database tables at a specific normalization stage.
Designed for A4 laser printer output (300 DPI, black & white).
"""

from __future__ import annotations

import logging

import matplotlib as mpl

mpl.use("Agg")
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# Common settings
DPI = 300
FONT_SIZE = 8
HEADER_COLOR = "#D0D0D0"
CELL_COLOR = "#FFFFFF"
HIGHLIGHT_COLOR = "#F0D0D0"  # light red-ish gray for violations
FIXED_COLOR = "#D0F0D0"  # light green-ish gray for fixed
FD_ARROW_COLOR = "#444444"


def _compute_col_widths(
    headers: list[str],
    rows: list[list[str]],
) -> list[float]:
    """Auto-calculate column widths based on content."""
    col_widths: list[float] = []
    for c in range(len(headers)):
        max_len = len(headers[c])
        for r in rows:
            if c < len(r):
                max_len = max(max_len, len(str(r[c])))
        col_widths.append(max(max_len * 0.08 + 0.1, 0.5))
    return col_widths


def draw_table(
    ax: Axes,
    x: float,
    y: float,
    title: str,
    headers: list[str],
    rows: list[list[str]],
    *,
    col_widths: list[float] | None = None,
    highlight_cols: set[int] | None = None,
    highlight_rows: set[int] | None = None,
    highlight_cells: set[tuple[int, int]] | None = None,
    strikethrough_cells: set[tuple[int, int]] | None = None,
    title_fontsize: int = 9,
) -> tuple[float, float]:
    """Draw a single table on the axes at position (x, y).

    Args:
        ax: matplotlib axes
        x: left position of the table
        y: top position of the table
        title: table title string
        headers: list of column header strings
        rows: list of lists (row data)
        col_widths: list of column widths (in inches-ish units)
        highlight_cols: set of column indices to highlight
        highlight_rows: set of row indices to highlight
        highlight_cells: set of (row, col) to highlight
        strikethrough_cells: set of (row, col) to draw strikethrough
        title_fontsize: font size for table title

    Returns:
        (width, height) of the drawn table
    """
    n_rows = len(rows)

    if col_widths is None:
        col_widths = _compute_col_widths(headers, rows)

    row_height = 0.22
    total_width = sum(col_widths)
    total_height = (n_rows + 1) * row_height  # +1 for header

    # Title
    ax.text(
        x + total_width / 2,
        y + 0.18,
        title,
        fontsize=title_fontsize,
        fontweight="bold",
        ha="center",
        va="bottom",
        family="monospace",
    )

    y_start = y

    # Draw header row
    cx = x
    for _c, (hdr, w) in enumerate(zip(headers, col_widths, strict=False)):
        color = HEADER_COLOR
        rect = mpatches.FancyBboxPatch(
            (cx, y_start),
            w,
            -row_height,
            boxstyle="square,pad=0",
            facecolor=color,
            edgecolor="black",
            linewidth=0.5,
        )
        ax.add_patch(rect)
        ax.text(
            cx + w / 2,
            y_start - row_height / 2,
            hdr,
            fontsize=FONT_SIZE,
            fontweight="bold",
            ha="center",
            va="center",
            family="monospace",
        )
        cx += w

    # Draw data rows
    for r_idx, row in enumerate(rows):
        cy = y_start - (r_idx + 1) * row_height
        cx = x
        for c_idx, (val, w) in enumerate(zip(row, col_widths, strict=False)):
            color = CELL_COLOR
            if highlight_cols and c_idx in highlight_cols:
                color = HIGHLIGHT_COLOR
            if highlight_rows and r_idx in highlight_rows:
                color = HIGHLIGHT_COLOR
            if highlight_cells and (r_idx, c_idx) in highlight_cells:
                color = HIGHLIGHT_COLOR

            rect = mpatches.FancyBboxPatch(
                (cx, cy),
                w,
                -row_height,
                boxstyle="square,pad=0",
                facecolor=color,
                edgecolor="black",
                linewidth=0.5,
            )
            ax.add_patch(rect)

            text_color = "black"
            ax.text(
                cx + w / 2,
                cy - row_height / 2,
                str(val),
                fontsize=FONT_SIZE,
                ha="center",
                va="center",
                family="monospace",
                color=text_color,
            )

            if strikethrough_cells and (r_idx, c_idx) in strikethrough_cells:
                ax.plot(
                    [cx + 0.03, cx + w - 0.03],
                    [cy - row_height / 2, cy - row_height / 2],
                    color="black",
                    linewidth=1.0,
                )

            cx += w

    return total_width, total_height + 0.25  # extra for title


def create_figure(
    width_inches: float = 11.69,
    height_inches: float = 8.27,
) -> tuple[Figure, Axes]:
    """Create A4 landscape figure."""
    fig, ax = plt.subplots(1, 1, figsize=(width_inches, height_inches), dpi=DPI)
    ax.set_xlim(0, width_inches)
    ax.set_ylim(0, height_inches)
    ax.axis("off")
    ax.set_aspect("equal")
    return fig, ax


def add_arrow(
    ax: Axes,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str = "",
    *,
    color: str = "black",
) -> None:
    """Draw an arrow with optional label."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": "->", "color": color, "lw": 1.5},
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mx,
            my + 0.12,
            label,
            fontsize=7,
            ha="center",
            va="bottom",
            family="monospace",
            color=color,
        )


def add_label(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    *,
    fontsize: int = 8,
    color: str = "black",
    ha: str = "left",
    style: str = "normal",
) -> None:
    """Add a text label."""
    ax.text(
        x,
        y,
        text,
        fontsize=fontsize,
        ha=ha,
        va="center",
        family="monospace",
        color=color,
        style=style,
    )


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Generating normalization diagrams...")

    from python_pkg.praca_magisterska_video.generate_images._norm_advanced import (
        draw_3nf,
        draw_4nf,
        draw_bcnf,
    )
    from python_pkg.praca_magisterska_video.generate_images._norm_basic import (
        draw_0nf,
        draw_1nf,
        draw_2nf,
    )
    from python_pkg.praca_magisterska_video.generate_images._norm_higher import (
        draw_5nf,
        draw_summary_flow,
    )

    draw_0nf()
    draw_1nf()
    draw_2nf()
    draw_3nf()
    draw_bcnf()
    draw_4nf()
    draw_5nf()
    draw_summary_flow()
    logger.info("Done! All diagrams saved to %s", OUTPUT_DIR)

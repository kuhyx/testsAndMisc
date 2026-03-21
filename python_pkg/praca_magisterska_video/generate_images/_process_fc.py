"""Classic flowchart diagram generator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
    BG_COLOR,
    DPI,
    FONT_SIZE,
    LINE_COLOR,
    OUTPUT_DIR,
    TITLE_SIZE,
    draw_arrow,
    draw_diamond,
    draw_line,
)

_logger = logging.getLogger(__name__)


# =========================================================================
# 4. Classic Flowchart
# =========================================================================


def _draw_fc_terminal(
    ax: Axes,
    x: float,
    y: float,
    text: str,
) -> None:
    """Draw a flowchart terminal (rounded) shape."""
    w, h = 20, 5.5
    rect = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=1.0",
        lw=2,
        edgecolor=LINE_COLOR,
        facecolor="#E0E0E0",
    )
    ax.add_patch(rect)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=FONT_SIZE,
        fontweight="bold",
    )


def _draw_fc_process_box(
    ax: Axes,
    x: float,
    y: float,
    text: str,
) -> None:
    """Draw a flowchart process box (rectangle)."""
    w, h = 26, 6
    rect = plt.Rectangle(
        (x - w / 2, y - h / 2),
        w,
        h,
        lw=1.5,
        edgecolor=LINE_COLOR,
        facecolor="white",
    )
    ax.add_patch(rect)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=FONT_SIZE,
    )


def _draw_fc_io_shape(
    ax: Axes,
    x: float,
    y: float,
    text: str,
) -> None:
    """Draw a flowchart I/O parallelogram."""
    w, h = 26, 5.5
    skew = 3
    verts = [
        (x - w / 2 + skew, y + h / 2),
        (x + w / 2 + skew, y + h / 2),
        (x + w / 2 - skew, y - h / 2),
        (x - w / 2 - skew, y - h / 2),
        (x - w / 2 + skew, y + h / 2),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.LINETO,
        MplPath.LINETO,
        MplPath.LINETO,
        MplPath.CLOSEPOLY,
    ]
    patch = mpatches.PathPatch(
        MplPath(verts, codes),
        facecolor="white",
        edgecolor=LINE_COLOR,
        lw=1.5,
    )
    ax.add_patch(patch)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=FONT_SIZE,
    )


def _draw_fc_elements(ax: Axes) -> None:
    """Draw all flowchart elements."""
    cx = 50
    y = 103
    step = 11

    _draw_fc_terminal(ax, cx, y, "START")

    y -= step
    _draw_fc_io_shape(ax, cx, y, "Reklamacja od klienta")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)

    y -= step
    _draw_fc_process_box(ax, cx, y, "Przyjmij zg\u0142oszenie")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 3)

    y -= step
    _draw_fc_process_box(
        ax,
        cx,
        y,
        "Zweryfikuj zasadno\u015b\u0107",
    )
    draw_arrow(ax, cx, y + step - 3, cx, y + 3)

    y -= step
    draw_diamond(ax, cx, y, 4.5, "Zasadna?")
    draw_arrow(ax, cx, y + step - 3, cx, y + 4.5)
    dec_y = y

    left_x = cx - 26
    _draw_fc_process_box(
        ax,
        left_x,
        dec_y,
        "Przygotuj wymian\u0119/zwrot",
    )
    draw_line(ax, cx - 4.5, dec_y, left_x + 13, dec_y)
    ax.text(
        cx - 7,
        dec_y + 2,
        "Tak",
        fontsize=8,
        ha="center",
        fontweight="bold",
    )

    right_x = cx + 26
    _draw_fc_process_box(
        ax,
        right_x,
        dec_y,
        "Odrzu\u0107 reklamacj\u0119",
    )
    draw_line(ax, cx + 4.5, dec_y, right_x - 13, dec_y)
    ax.text(
        cx + 7,
        dec_y + 2,
        "Nie",
        fontsize=8,
        ha="center",
        fontweight="bold",
    )

    merge_y = dec_y - step
    draw_line(ax, left_x, dec_y - 3, left_x, merge_y)
    draw_line(ax, right_x, dec_y - 3, right_x, merge_y)
    draw_line(ax, left_x, merge_y, right_x, merge_y)
    ax.plot(cx, merge_y, "ko", markersize=4)

    y = merge_y - step + 3
    _draw_fc_process_box(ax, cx, y, "Powiadom klienta")
    draw_arrow(ax, cx, merge_y, cx, y + 3)

    y -= step
    _draw_fc_io_shape(
        ax,
        cx,
        y,
        "Odpowied\u017a do klienta",
    )
    draw_arrow(ax, cx, y + step - 3, cx, y + 2.8)

    y -= step
    _draw_fc_terminal(ax, cx, y, "KONIEC")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)


def _draw_fc_legend(ax: Axes) -> None:
    """Draw flowchart legend."""
    ly = 4
    ax.text(
        5,
        ly,
        "Legenda:",
        fontsize=7,
        fontweight="bold",
        va="center",
    )
    _draw_fc_terminal(ax, 18, ly, "")
    ax.text(
        18,
        ly,
        "Start/\nKoniec",
        fontsize=5.5,
        ha="center",
        va="center",
    )
    w, h = 9, 3
    ax.add_patch(
        plt.Rectangle(
            (32 - w / 2, ly - h / 2),
            w,
            h,
            lw=1.5,
            edgecolor=LINE_COLOR,
            facecolor="white",
        )
    )
    ax.text(32, ly, "Proces", fontsize=6, ha="center", va="center")
    draw_diamond(ax, 46, ly, 2)
    ax.text(49.5, ly, "= Decyzja", fontsize=6, va="center")
    skew = 1.5
    w2, h2 = 9, 3
    verts = [
        (62 - w2 / 2 + skew, ly + h2 / 2),
        (62 + w2 / 2 + skew, ly + h2 / 2),
        (62 + w2 / 2 - skew, ly - h2 / 2),
        (62 - w2 / 2 - skew, ly - h2 / 2),
        (62 - w2 / 2 + skew, ly + h2 / 2),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.LINETO,
        MplPath.LINETO,
        MplPath.LINETO,
        MplPath.CLOSEPOLY,
    ]
    ax.add_patch(
        mpatches.PathPatch(
            MplPath(verts, codes),
            facecolor="white",
            edgecolor=LINE_COLOR,
            lw=1.2,
        )
    )
    ax.text(62, ly, "We/Wy", fontsize=6, ha="center", va="center")


def generate_flowchart() -> None:
    """Generate flowchart."""
    fig, ax = plt.subplots(figsize=(8.27, 11))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 110)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_title(
        "Schemat blokowy (Flowchart) \u2014 Obs\u0142uga reklamacji",
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=12,
    )

    _draw_fc_elements(ax)
    _draw_fc_legend(ax)

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "flowchart_reklamacja.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK Flowchart saved")

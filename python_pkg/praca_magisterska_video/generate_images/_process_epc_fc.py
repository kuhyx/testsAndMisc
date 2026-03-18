"""EPC diagram generator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
    BG_COLOR,
    DPI,
    LINE_COLOR,
    OUTPUT_DIR,
    TITLE_SIZE,
    draw_arrow,
    draw_line,
)

_logger = logging.getLogger(__name__)


# =========================================================================
# 3. EPC (Event-driven Process Chain)
# =========================================================================


def _draw_epc_event(
    ax: Axes,
    x: float,
    y: float,
    text: str,
) -> None:
    """Draw an EPC event shape (rounded grey box)."""
    w, h = 26, 5.5
    rect = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.5",
        lw=1.5,
        edgecolor=LINE_COLOR,
        facecolor="#D8D8D8",
    )
    ax.add_patch(rect)
    ax.text(x, y, text, ha="center", va="center", fontsize=8)


def _draw_epc_function(
    ax: Axes,
    x: float,
    y: float,
    text: str,
) -> None:
    """Draw an EPC function shape (rounded white box, bold)."""
    w, h = 26, 5.5
    rect = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.3",
        lw=2,
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
        fontsize=8,
        fontweight="bold",
    )


def _draw_epc_connector(
    ax: Axes,
    x: float,
    y: float,
    text: str,
) -> None:
    """Draw an EPC logical connector (circle)."""
    circle = plt.Circle(
        (x, y),
        2.8,
        lw=1.5,
        edgecolor=LINE_COLOR,
        facecolor="white",
    )
    ax.add_patch(circle)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
    )


def _draw_epc_flow(
    ax: Axes,
) -> tuple[float, float, float]:
    """Draw sequential EPC flow from E1 through XOR split."""
    cx = 50
    y = 114
    step = 9.5

    _draw_epc_event(ax, cx, y, "Reklamacja wp\u0142yn\u0119\u0142a")

    y -= step
    _draw_epc_function(ax, cx, y, "Przyjmij zg\u0142oszenie")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)

    y -= step
    _draw_epc_event(ax, cx, y, "Zg\u0142oszenie przyj\u0119te")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)

    y -= step
    _draw_epc_function(ax, cx, y, "Zweryfikuj zasadno\u015b\u0107")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)

    y -= step
    _draw_epc_event(ax, cx, y, "Zasadno\u015b\u0107 oceniona")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)

    y -= step
    _draw_epc_connector(ax, cx, y, "XOR")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)

    return cx, y, step


def _draw_epc_branches(
    ax: Axes,
    cx: float,
    split_y: float,
    step: float,
) -> None:
    """Draw EPC branches, merge, and post-merge elements."""
    left_x = cx - 28
    right_x = cx + 28

    by = split_y - step
    _draw_epc_event(ax, left_x, by, "Reklamacja zasadna")
    draw_line(ax, cx - 2.8, split_y, left_x, split_y)
    draw_arrow(ax, left_x, split_y, left_x, by + 2.8)

    by2 = by - step
    _draw_epc_function(
        ax,
        left_x,
        by2,
        "Przygotuj wymian\u0119/zwrot",
    )
    draw_arrow(ax, left_x, by - 2.8, left_x, by2 + 2.8)

    by3 = by2 - step
    _draw_epc_event(ax, left_x, by3, "Wymiana przygotowana")
    draw_arrow(ax, left_x, by2 - 2.8, left_x, by3 + 2.8)

    _draw_epc_event(ax, right_x, by, "Reklamacja niezasadna")
    draw_line(ax, cx + 2.8, split_y, right_x, split_y)
    draw_arrow(ax, right_x, split_y, right_x, by + 2.8)

    _draw_epc_function(ax, right_x, by2, "Odrzu\u0107 reklamacj\u0119")
    draw_arrow(ax, right_x, by - 2.8, right_x, by2 + 2.8)

    _draw_epc_event(ax, right_x, by3, "Reklamacja odrzucona")
    draw_arrow(ax, right_x, by2 - 2.8, right_x, by3 + 2.8)

    merge_y = by3 - step
    _draw_epc_connector(ax, cx, merge_y, "XOR")
    draw_line(ax, left_x, by3 - 2.8, left_x, merge_y)
    draw_line(ax, left_x, merge_y, cx - 2.8, merge_y)
    draw_line(ax, right_x, by3 - 2.8, right_x, merge_y)
    draw_line(ax, right_x, merge_y, cx + 2.8, merge_y)

    y = merge_y - step
    _draw_epc_function(ax, cx, y, "Powiadom klienta")
    draw_arrow(ax, cx, merge_y - 2.8, cx, y + 2.8)

    y -= step
    _draw_epc_event(ax, cx, y, "Klient powiadomiony")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)


def _draw_epc_legend(ax: Axes) -> None:
    """Draw EPC legend."""
    ly = 3
    _draw_epc_event(ax, 16, ly, "Zdarzenie")
    _draw_epc_function(ax, 46, ly, "Funkcja")
    _draw_epc_connector(ax, 68, ly, "XOR")
    ax.text(
        72,
        ly,
        "= \u0141\u0105cznik logiczny",
        fontsize=7,
        va="center",
    )


def generate_epc() -> None:
    """Generate epc."""
    fig, ax = plt.subplots(figsize=(8.27, 11))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 120)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_title(
        "EPC (Event-driven Process Chain)" " \u2014 Obs\u0142uga reklamacji",
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=12,
    )

    cx, split_y, step = _draw_epc_flow(ax)
    _draw_epc_branches(ax, cx, split_y, step)
    _draw_epc_legend(ax)

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "epc_reklamacja.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK EPC saved")

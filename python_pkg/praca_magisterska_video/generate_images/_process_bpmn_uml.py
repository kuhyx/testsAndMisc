"""BPMN and UML activity diagram generators."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

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
    draw_diamond,
    draw_line,
    draw_rounded_rect,
)

_logger = logging.getLogger(__name__)

# 1. BPMN 2.0 Diagram
# =========================================================================


def _draw_bpmn_pool_and_lanes(
    ax: Axes,
) -> tuple[float, float, float, float]:
    """Draw BPMN pool outline and swim lanes, return lane positions."""
    pool_x, pool_y, pool_w, pool_h = 3, 3, 104, 68
    ax.add_patch(
        plt.Rectangle(
            (pool_x, pool_y),
            pool_w,
            pool_h,
            lw=2,
            edgecolor=LINE_COLOR,
            facecolor="white",
        )
    )

    label_strip = pool_x + 4
    ax.plot(
        [label_strip, label_strip],
        [pool_y, pool_y + pool_h],
        color=LINE_COLOR,
        lw=1.5,
    )
    ax.text(
        pool_x + 2,
        pool_y + pool_h / 2,
        "FIRMA",
        fontsize=11,
        fontweight="bold",
        rotation=90,
        ha="center",
        va="center",
    )

    lane_top = pool_y + pool_h
    lane_mid1 = pool_y + pool_h * 2 / 3
    lane_mid2 = pool_y + pool_h * 1 / 3

    ax.plot(
        [label_strip, pool_x + pool_w],
        [lane_mid1, lane_mid1],
        color=LINE_COLOR,
        lw=1,
    )
    ax.plot(
        [label_strip, pool_x + pool_w],
        [lane_mid2, lane_mid2],
        color=LINE_COLOR,
        lw=1,
    )

    y_bok = (lane_top + lane_mid1) / 2
    y_jak = (lane_mid1 + lane_mid2) / 2
    y_mag = (lane_mid2 + pool_y) / 2

    ax.text(
        label_strip + 2.5,
        y_bok,
        "BOK",
        fontsize=8,
        ha="center",
        va="center",
        rotation=90,
        fontstyle="italic",
    )
    ax.text(
        label_strip + 2.5,
        y_jak,
        "Jako\u015b\u0107",
        fontsize=8,
        ha="center",
        va="center",
        rotation=90,
        fontstyle="italic",
    )
    ax.text(
        label_strip + 2.5,
        y_mag,
        "Magazyn",
        fontsize=8,
        ha="center",
        va="center",
        rotation=90,
        fontstyle="italic",
    )

    content_left = label_strip + 5
    return y_bok, y_jak, y_mag, content_left


def _draw_bpmn_elements(
    ax: Axes,
    y_bok: float,
    y_jak: float,
    y_mag: float,
    content_left: float,
) -> None:
    """Draw all BPMN tasks, gateways, and events."""
    sx = content_left + 4
    ax.add_patch(
        plt.Circle(
            (sx, y_bok),
            2,
            lw=2,
            edgecolor=LINE_COLOR,
            facecolor="white",
        )
    )
    ax.text(
        sx,
        y_bok - 3.5,
        "Reklamacja\nwp\u0142ywa",
        fontsize=6,
        ha="center",
    )

    t1x = sx + 14
    draw_rounded_rect(ax, t1x, y_bok, 14, 6, "Przyjmij\nzg\u0142oszenie")
    draw_arrow(ax, sx + 2, y_bok, t1x - 7, y_bok)

    t2x = t1x + 18
    draw_rounded_rect(
        ax,
        t2x,
        y_jak,
        14,
        6,
        "Zweryfikuj\nzasadno\u015b\u0107",
    )
    elbow_x = t1x + 10
    draw_line(ax, t1x + 7, y_bok, elbow_x, y_bok)
    draw_line(ax, elbow_x, y_bok, elbow_x, y_jak)
    draw_arrow(ax, elbow_x, y_jak, t2x - 7, y_jak)

    gx = t2x + 14
    draw_diamond(ax, gx, y_jak, 3.5, "X")
    draw_arrow(ax, t2x + 7, y_jak, gx - 3.5, y_jak)

    t3x = gx + 14
    draw_rounded_rect(
        ax,
        t3x,
        y_mag,
        14,
        6,
        "Przygotuj\nwymian\u0119/zwrot",
    )
    draw_line(ax, gx, y_jak - 3.5, gx, y_mag)
    draw_arrow(ax, gx, y_mag, t3x - 7, y_mag)
    ax.text(gx + 1.5, y_jak - 6, "Tak", fontsize=7, ha="left")

    t4x = gx + 14
    draw_rounded_rect(
        ax,
        t4x,
        y_jak,
        14,
        6,
        "Odrzu\u0107\nreklamacj\u0119",
    )
    draw_arrow(ax, gx + 3.5, y_jak, t4x - 7, y_jak)
    ax.text(gx + 4, y_jak + 2, "Nie", fontsize=7, ha="left")

    mx = t4x + 14
    draw_diamond(ax, mx, y_bok, 3.5, "X")
    draw_line(ax, t4x + 7, y_jak, mx, y_jak)
    draw_arrow(ax, mx, y_jak, mx, y_bok - 3.5)
    draw_line(ax, t3x + 7, y_mag, mx - 4, y_mag)
    draw_line(ax, mx - 4, y_mag, mx - 4, y_bok)
    draw_arrow(ax, mx - 4, y_bok, mx - 3.5, y_bok)

    t5x = mx + 13
    draw_rounded_rect(ax, t5x, y_bok, 14, 6, "Powiadom\nklienta")
    draw_arrow(ax, mx + 3.5, y_bok, t5x - 7, y_bok)

    ex = t5x + 12
    ax.add_patch(
        plt.Circle(
            (ex, y_bok),
            2,
            lw=3,
            edgecolor=LINE_COLOR,
            facecolor="white",
        )
    )
    draw_arrow(ax, t5x + 7, y_bok, ex - 2, y_bok)
    ax.text(ex, y_bok - 3.5, "Koniec", fontsize=6, ha="center")


def _draw_bpmn_legend(ax: Axes) -> None:
    """Draw BPMN legend."""
    ly = 1
    ax.text(
        12,
        ly,
        "Legenda:",
        fontsize=7,
        fontweight="bold",
        va="center",
    )
    ax.add_patch(
        plt.Circle(
            (22, ly),
            1,
            lw=2,
            edgecolor=LINE_COLOR,
            facecolor="white",
        )
    )
    ax.text(24, ly, "Start", fontsize=6, va="center")
    ax.add_patch(
        plt.Circle(
            (30, ly),
            1,
            lw=3,
            edgecolor=LINE_COLOR,
            facecolor="white",
        )
    )
    ax.text(32, ly, "Koniec", fontsize=6, va="center")
    draw_diamond(ax, 40, ly, 1.5, "X", fontsize=5)
    ax.text(43, ly, "Bramka XOR", fontsize=6, va="center")
    draw_rounded_rect(ax, 58, ly, 7, 2.5, "Zadanie", fontsize=6)
    ax.text(65, ly, "Sequence Flow \u2192", fontsize=6, va="center")


def generate_bpmn() -> None:
    """Generate bpmn."""
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 75)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_title(
        "BPMN 2.0 \u2014 Obs\u0142uga reklamacji",
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=12,
    )

    y_bok, y_jak, y_mag, content_left = _draw_bpmn_pool_and_lanes(ax)
    _draw_bpmn_elements(ax, y_bok, y_jak, y_mag, content_left)
    _draw_bpmn_legend(ax)

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "bpmn_reklamacja.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK BPMN saved")


# =========================================================================
# 2. UML Activity Diagram
# =========================================================================


def _draw_uml_elements(ax: Axes) -> None:
    """Draw all UML activity diagram elements."""
    cx = 50
    y = 93
    step = 11

    ax.add_patch(
        plt.Circle((cx, y), 1.8, facecolor="black", edgecolor="black"),
    )

    y -= step
    draw_rounded_rect(
        ax,
        cx,
        y,
        28,
        6,
        "Przyjmij zg\u0142oszenie reklamacji",
    )
    draw_arrow(ax, cx, y + step - 1.8, cx, y + 3)

    y -= step
    draw_rounded_rect(
        ax,
        cx,
        y,
        28,
        6,
        "Zweryfikuj zasadno\u015b\u0107",
    )
    draw_arrow(ax, cx, y + step - 3, cx, y + 3)

    y -= step
    draw_diamond(ax, cx, y, 4)
    draw_arrow(ax, cx, y + step - 3, cx, y + 4)
    ax.text(
        cx + 6,
        y + 5,
        "[zasadna?]",
        fontsize=8,
        fontstyle="italic",
    )

    dec_y = y
    branch_y = dec_y - step

    left_x = cx - 24
    draw_rounded_rect(
        ax,
        left_x,
        branch_y,
        22,
        6,
        "Przygotuj\nwymian\u0119/zwrot",
    )
    draw_line(ax, cx - 4, dec_y, left_x, dec_y)
    draw_arrow(ax, left_x, dec_y, left_x, branch_y + 3)
    ax.text(
        left_x + 2,
        dec_y + 1.5,
        "[tak]",
        fontsize=8,
        fontstyle="italic",
    )

    right_x = cx + 24
    draw_rounded_rect(
        ax,
        right_x,
        branch_y,
        22,
        6,
        "Odrzu\u0107\nreklamacj\u0119",
    )
    draw_line(ax, cx + 4, dec_y, right_x, dec_y)
    draw_arrow(ax, right_x, dec_y, right_x, branch_y + 3)
    ax.text(
        right_x - 12,
        dec_y + 1.5,
        "[nie]",
        fontsize=8,
        fontstyle="italic",
    )

    merge_y = branch_y - step
    draw_diamond(ax, cx, merge_y, 4)
    draw_line(ax, left_x, branch_y - 3, left_x, merge_y)
    draw_line(ax, left_x, merge_y, cx - 4, merge_y)
    draw_line(ax, right_x, branch_y - 3, right_x, merge_y)
    draw_line(ax, right_x, merge_y, cx + 4, merge_y)

    y = merge_y - step
    draw_rounded_rect(ax, cx, y, 28, 6, "Powiadom klienta")
    draw_arrow(ax, cx, merge_y - 4, cx, y + 3)

    ey = y - step
    ax.add_patch(
        plt.Circle(
            (cx, ey),
            2.5,
            lw=2,
            facecolor="white",
            edgecolor="black",
        )
    )
    ax.add_patch(
        plt.Circle((cx, ey), 1.5, facecolor="black", edgecolor="black"),
    )
    draw_arrow(ax, cx, y - 3, cx, ey + 2.5)


def _draw_uml_legend(ax: Axes) -> None:
    """Draw UML activity diagram legend."""
    ly = 5
    ax.add_patch(
        plt.Circle((12, ly), 1.2, facecolor="black", edgecolor="black"),
    )
    ax.text(15, ly, "= Pocz\u0105tek", fontsize=7, va="center")
    ax.add_patch(
        plt.Circle(
            (32, ly),
            1.3,
            lw=2,
            facecolor="white",
            edgecolor="black",
        )
    )
    ax.add_patch(
        plt.Circle((32, ly), 0.8, facecolor="black", edgecolor="black"),
    )
    ax.text(35, ly, "= Koniec", fontsize=7, va="center")
    draw_diamond(ax, 50, ly, 1.5)
    ax.text(53, ly, "= Decyzja/Merge", fontsize=7, va="center")
    draw_rounded_rect(ax, 78, ly, 9, 3, "Akcja", fontsize=7)


def generate_uml_activity() -> None:
    """Generate uml activity."""
    fig, ax = plt.subplots(figsize=(8.27, 10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_title(
        "UML Activity Diagram \u2014 Obs\u0142uga reklamacji",
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=12,
    )

    _draw_uml_elements(ax)
    _draw_uml_legend(ax)

    fig.tight_layout()
    fig.savefig(
        str(Path(OUTPUT_DIR) / "uml_activity_reklamacja.png"),
        dpi=DPI,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(fig)
    _logger.info("  OK UML Activity saved")

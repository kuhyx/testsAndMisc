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

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt

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
    ax: Axes, x1: float, y1: float, x2: float, y2: float,
) -> None:
    """Draw arrow."""
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": "->", "color": LINE_COLOR, "lw": 1.3},
    )


def draw_line(
    ax: Axes, x1: float, y1: float, x2: float, y2: float,
) -> None:
    """Draw line."""
    ax.plot(
        [x1, x2], [y1, y2],
        color=LINE_COLOR, lw=1.3, solid_capstyle="round",
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
            (sx, y_bok), 2, lw=2, edgecolor=LINE_COLOR, facecolor="white",
        )
    )
    ax.text(
        sx, y_bok - 3.5, "Reklamacja\nwp\u0142ywa", fontsize=6, ha="center",
    )

    t1x = sx + 14
    draw_rounded_rect(ax, t1x, y_bok, 14, 6, "Przyjmij\nzg\u0142oszenie")
    draw_arrow(ax, sx + 2, y_bok, t1x - 7, y_bok)

    t2x = t1x + 18
    draw_rounded_rect(
        ax, t2x, y_jak, 14, 6, "Zweryfikuj\nzasadno\u015b\u0107",
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
        ax, t3x, y_mag, 14, 6, "Przygotuj\nwymian\u0119/zwrot",
    )
    draw_line(ax, gx, y_jak - 3.5, gx, y_mag)
    draw_arrow(ax, gx, y_mag, t3x - 7, y_mag)
    ax.text(gx + 1.5, y_jak - 6, "Tak", fontsize=7, ha="left")

    t4x = gx + 14
    draw_rounded_rect(
        ax, t4x, y_jak, 14, 6, "Odrzu\u0107\nreklamacj\u0119",
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
            (ex, y_bok), 2, lw=3, edgecolor=LINE_COLOR, facecolor="white",
        )
    )
    draw_arrow(ax, t5x + 7, y_bok, ex - 2, y_bok)
    ax.text(ex, y_bok - 3.5, "Koniec", fontsize=6, ha="center")


def _draw_bpmn_legend(ax: Axes) -> None:
    """Draw BPMN legend."""
    ly = 1
    ax.text(
        12, ly, "Legenda:", fontsize=7, fontweight="bold", va="center",
    )
    ax.add_patch(
        plt.Circle(
            (22, ly), 1, lw=2, edgecolor=LINE_COLOR, facecolor="white",
        )
    )
    ax.text(24, ly, "Start", fontsize=6, va="center")
    ax.add_patch(
        plt.Circle(
            (30, ly), 1, lw=3, edgecolor=LINE_COLOR, facecolor="white",
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
        ax, cx, y, 28, 6, "Przyjmij zg\u0142oszenie reklamacji",
    )
    draw_arrow(ax, cx, y + step - 1.8, cx, y + 3)

    y -= step
    draw_rounded_rect(
        ax, cx, y, 28, 6, "Zweryfikuj zasadno\u015b\u0107",
    )
    draw_arrow(ax, cx, y + step - 3, cx, y + 3)

    y -= step
    draw_diamond(ax, cx, y, 4)
    draw_arrow(ax, cx, y + step - 3, cx, y + 4)
    ax.text(
        cx + 6, y + 5, "[zasadna?]", fontsize=8, fontstyle="italic",
    )

    dec_y = y
    branch_y = dec_y - step

    left_x = cx - 24
    draw_rounded_rect(
        ax, left_x, branch_y, 22, 6, "Przygotuj\nwymian\u0119/zwrot",
    )
    draw_line(ax, cx - 4, dec_y, left_x, dec_y)
    draw_arrow(ax, left_x, dec_y, left_x, branch_y + 3)
    ax.text(
        left_x + 2, dec_y + 1.5, "[tak]",
        fontsize=8, fontstyle="italic",
    )

    right_x = cx + 24
    draw_rounded_rect(
        ax, right_x, branch_y, 22, 6, "Odrzu\u0107\nreklamacj\u0119",
    )
    draw_line(ax, cx + 4, dec_y, right_x, dec_y)
    draw_arrow(ax, right_x, dec_y, right_x, branch_y + 3)
    ax.text(
        right_x - 12, dec_y + 1.5, "[nie]",
        fontsize=8, fontstyle="italic",
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
            (cx, ey), 2.5, lw=2, facecolor="white", edgecolor="black",
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
            (32, ly), 1.3, lw=2, facecolor="white", edgecolor="black",
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


# =========================================================================
# 3. EPC (Event-driven Process Chain)
# =========================================================================


def _draw_epc_event(
    ax: Axes, x: float, y: float, text: str,
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
    ax: Axes, x: float, y: float, text: str,
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
        x, y, text,
        ha="center", va="center", fontsize=8, fontweight="bold",
    )


def _draw_epc_connector(
    ax: Axes, x: float, y: float, text: str,
) -> None:
    """Draw an EPC logical connector (circle)."""
    circle = plt.Circle(
        (x, y), 2.8, lw=1.5, edgecolor=LINE_COLOR, facecolor="white",
    )
    ax.add_patch(circle)
    ax.text(
        x, y, text,
        ha="center", va="center", fontsize=9, fontweight="bold",
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
        ax, left_x, by2, "Przygotuj wymian\u0119/zwrot",
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
        72, ly, "= \u0141\u0105cznik logiczny", fontsize=7, va="center",
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
        "EPC (Event-driven Process Chain)"
        " \u2014 Obs\u0142uga reklamacji",
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


# =========================================================================
# 4. Classic Flowchart
# =========================================================================


def _draw_fc_terminal(
    ax: Axes, x: float, y: float, text: str,
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
    ax: Axes, x: float, y: float, text: str,
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
        x, y, text, ha="center", va="center", fontsize=FONT_SIZE,
    )


def _draw_fc_io_shape(
    ax: Axes, x: float, y: float, text: str,
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
        x, y, text, ha="center", va="center", fontsize=FONT_SIZE,
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
        ax, cx, y, "Zweryfikuj zasadno\u015b\u0107",
    )
    draw_arrow(ax, cx, y + step - 3, cx, y + 3)

    y -= step
    draw_diamond(ax, cx, y, 4.5, "Zasadna?")
    draw_arrow(ax, cx, y + step - 3, cx, y + 4.5)
    dec_y = y

    left_x = cx - 26
    _draw_fc_process_box(
        ax, left_x, dec_y, "Przygotuj wymian\u0119/zwrot",
    )
    draw_line(ax, cx - 4.5, dec_y, left_x + 13, dec_y)
    ax.text(
        cx - 7, dec_y + 2, "Tak",
        fontsize=8, ha="center", fontweight="bold",
    )

    right_x = cx + 26
    _draw_fc_process_box(
        ax, right_x, dec_y, "Odrzu\u0107 reklamacj\u0119",
    )
    draw_line(ax, cx + 4.5, dec_y, right_x - 13, dec_y)
    ax.text(
        cx + 7, dec_y + 2, "Nie",
        fontsize=8, ha="center", fontweight="bold",
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
        ax, cx, y, "Odpowied\u017a do klienta",
    )
    draw_arrow(ax, cx, y + step - 3, cx, y + 2.8)

    y -= step
    _draw_fc_terminal(ax, cx, y, "KONIEC")
    draw_arrow(ax, cx, y + step - 2.8, cx, y + 2.8)


def _draw_fc_legend(ax: Axes) -> None:
    """Draw flowchart legend."""
    ly = 4
    ax.text(
        5, ly, "Legenda:", fontsize=7, fontweight="bold", va="center",
    )
    _draw_fc_terminal(ax, 18, ly, "")
    ax.text(
        18, ly, "Start/\nKoniec",
        fontsize=5.5, ha="center", va="center",
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
        "Schemat blokowy (Flowchart)"
        " \u2014 Obs\u0142uga reklamacji",
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


# =========================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _logger.info("Generating diagrams to %s/...", OUTPUT_DIR)
    generate_bpmn()
    generate_uml_activity()
    generate_epc()
    generate_flowchart()
    _logger.info("\nAll 4 diagrams saved to %s/", OUTPUT_DIR)
    for fname in sorted(p.name for p in Path(OUTPUT_DIR).iterdir()):
        if fname.endswith(".png"):
            size_kb = (
                Path(
                    str(Path(OUTPUT_DIR).stat().st_size / fname),
                )
                / 1024
            )
            _logger.info("  %s (%.0f KB)", fname, size_kb)

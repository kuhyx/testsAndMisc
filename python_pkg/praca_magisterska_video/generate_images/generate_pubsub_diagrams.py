#!/usr/bin/env python3
"""Generate Pub/Sub diagrams for PYTANIE 19.

  Subscription types (4 separate images):
    1. Topic-based
    2. Content-based
    3. Type-based
    4. Hierarchical (wildcards)
  Delivery guarantees (3 separate images):
    5. At-most-once
    6. At-least-once
    7. Exactly-once.

All: A4-width, B&W, 300 DPI, laser-printer-friendly.
One diagram per image -- no cramming.
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
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

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
    logger.info("  \u2713 %s", name)


# ============================================================
# 1. Topic-based subscription
# ============================================================
def draw_sub_topic() -> None:
    """Draw sub topic."""
    fig, ax = plt.subplots(1, 1, figsize=(FIG_W, 4.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Subskrypcja topic-based"
        " \u2014 routing po nazwie tematu",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bold10 = BoxStyle(
        fill=GRAY1, fontsize=10, fontweight="bold"
    )
    fs85 = BoxStyle(fill=GRAY1, fontsize=8.5)

    draw_box(
        ax, (0.2, 3.2), (2.4, 1.1), "Publisher", bold10
    )
    draw_box(
        ax,
        (0.3, 1.8),
        (2.2, 0.8),
        'topic: "orders"',
        BoxStyle(fill=GRAY4, fontsize=8),
    )
    draw_box(
        ax,
        (0.3, 0.7),
        (2.2, 0.8),
        'topic: "payments"',
        BoxStyle(fill=GRAY4, fontsize=8),
    )

    draw_box(
        ax,
        (4.2, 1.5),
        (2.8, 2.2),
        "BROKER\n\ntopic routing",
        BoxStyle(
            fill=GRAY2, fontsize=10, fontweight="bold"
        ),
    )

    draw_box(
        ax,
        (8.5, 3.8),
        (3.0, 1.0),
        'Subscriber A\nsubskrybuje: "orders"',
        fs85,
    )
    draw_box(
        ax,
        (8.5, 2.2),
        (3.0, 1.0),
        'Subscriber B\nsubskrybuje: "payments"',
        fs85,
    )
    draw_box(
        ax,
        (8.5, 0.6),
        (3.0, 1.0),
        'Subscriber C\nsubskrybuje: "orders"',
        fs85,
    )

    fs8 = ArrowCfg(label_fs=8)
    draw_arrow(ax, (2.6, 2.2), (4.2, 2.8), fs8)
    draw_arrow(ax, (2.6, 1.1), (4.2, 2.2), fs8)

    draw_arrow(
        ax,
        (7.0, 3.4),
        (8.5, 4.2),
        ArrowCfg(label='"orders"', label_fs=8),
    )
    draw_arrow(
        ax,
        (7.0, 2.6),
        (8.5, 2.7),
        ArrowCfg(label='"payments"', label_fs=8),
    )
    draw_arrow(
        ax,
        (7.0, 2.2),
        (8.5, 1.2),
        ArrowCfg(label='"orders"', label_fs=8),
    )

    ax.text(
        6.0,
        0.1,
        "Subscriber deklaruje nazw\u0119 tematu."
        " Broker kieruje wiadomo\u015bci\n"
        "do WSZYSTKICH subscriber\u00f3w"
        " danego tematu. Najprostszy model.",
        ha="center",
        va="bottom",
        fontsize=8.5,
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    save(fig, "pubsub_sub_topic.png")


# ============================================================
# 2. Content-based subscription
# ============================================================
def draw_sub_content() -> None:
    """Draw sub content."""
    fig, ax = plt.subplots(1, 1, figsize=(FIG_W, 4.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Subskrypcja content-based"
        " \u2014 filtrowanie po tre\u015bci wiadomo\u015bci",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bold10 = BoxStyle(
        fill=GRAY1, fontsize=10, fontweight="bold"
    )
    draw_box(
        ax, (0.2, 3.5), (2.4, 1.1), "Publisher", bold10
    )
    draw_box(
        ax,
        (0.2, 1.8),
        (2.4, 1.2),
        'price: 150\ntype: "book"\ncategory: "IT"',
        BoxStyle(fill=GRAY4, fontsize=8.5),
    )

    draw_box(
        ax,
        (4.0, 2.0),
        (3.0, 2.5),
        "BROKER\n\newaluuje filtry\n"
        "ka\u017cdego subscribera",
        BoxStyle(
            fill=GRAY2, fontsize=9, fontweight="bold"
        ),
    )

    fs9 = BoxStyle(fill=GRAY1, fontsize=9)
    draw_box(
        ax,
        (8.5, 4.2),
        (3.2, 1.0),
        "Sub A\nfiltr: price > 100",
        fs9,
    )
    draw_box(
        ax,
        (8.5, 2.6),
        (3.2, 1.0),
        'Sub B\nfiltr: type = "food"',
        fs9,
    )
    draw_box(
        ax,
        (8.5, 1.0),
        (3.2, 1.0),
        "Sub C\nfiltr: price < 50",
        fs9,
    )

    draw_arrow(ax, (2.6, 2.4), (4.0, 3.0))
    draw_arrow(
        ax,
        (7.0, 4.0),
        (8.5, 4.6),
        ArrowCfg(
            label="150 > 100  \u2713  dostarczono",
            label_fs=8,
        ),
    )
    draw_dashed_arrow(
        ax,
        (7.0, 3.2),
        (8.5, 3.1),
        DashedCfg(
            label='"book" \u2260 "food"'
            "  \u2717  odrzucono",
            label_fs=8,
        ),
    )
    draw_dashed_arrow(
        ax,
        (7.0, 2.5),
        (8.5, 1.6),
        DashedCfg(
            label="150 < 50  \u2717  odrzucono",
            label_fs=8,
        ),
    )

    ax.text(
        6.0,
        0.2,
        "Broker analizuje TRE\u015a\u0106 wiadomo\u015bci"
        " i ewaluuje predykaty.\n"
        "Bardziej elastyczny ni\u017c topic-based,"
        " ale wolniejszy (koszt ewaluacji).",
        ha="center",
        va="bottom",
        fontsize=8.5,
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    save(fig, "pubsub_sub_content.png")


# ============================================================
# 3. Type-based subscription
# ============================================================
def draw_sub_type() -> None:
    """Draw sub type."""
    fig, ax = plt.subplots(1, 1, figsize=(FIG_W, 5.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Subskrypcja type-based"
        " \u2014 routing po typie (klasie) obiektu",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bold10 = BoxStyle(
        fill=GRAY1, fontsize=10, fontweight="bold"
    )
    draw_box(
        ax, (0.2, 4.2), (2.4, 1.1), "Publisher", bold10
    )

    fs9_g4 = BoxStyle(fill=GRAY4, fontsize=9)
    draw_box(
        ax,
        (0.1, 2.8),
        (2.6, 0.9),
        "new OrderEvent()",
        fs9_g4,
    )
    draw_box(
        ax,
        (0.1, 1.5),
        (2.6, 0.9),
        "new PaymentEvent()",
        fs9_g4,
    )

    draw_box(
        ax,
        (4.0, 2.3),
        (3.0, 2.4),
        "BROKER\n\nrouting po\ntypie klasy",
        BoxStyle(
            fill=GRAY2, fontsize=10, fontweight="bold"
        ),
    )

    fs9 = BoxStyle(fill=GRAY1, fontsize=9)
    draw_box(
        ax,
        (8.5, 4.8),
        (3.2, 1.0),
        "Sub A\n\u2192 OrderEvent",
        fs9,
    )
    draw_box(
        ax,
        (8.5, 3.2),
        (3.2, 1.0),
        "Sub B\n\u2192 PaymentEvent",
        fs9,
    )
    draw_box(
        ax,
        (8.5, 1.6),
        (3.2, 1.0),
        "Sub C\n\u2192 Event (base)",
        fs9,
    )

    draw_arrow(ax, (2.7, 3.2), (4.0, 3.8))
    draw_arrow(ax, (2.7, 2.0), (4.0, 3.0))
    draw_arrow(
        ax,
        (7.0, 4.3),
        (8.5, 5.2),
        ArrowCfg(label="OrderEvent", label_fs=8),
    )
    draw_arrow(
        ax,
        (7.0, 3.5),
        (8.5, 3.7),
        ArrowCfg(label="PaymentEvent", label_fs=8),
    )
    draw_arrow(
        ax,
        (7.0, 3.0),
        (8.5, 2.2),
        ArrowCfg(
            label="oba (dziedziczenie!)", label_fs=8
        ),
    )

    hx, hy = 0.5, 0.0
    draw_box(
        ax,
        (hx + 2.0, hy + 0.2),
        (1.8, 0.6),
        "Event",
        BoxStyle(
            fill=GRAY3, fontsize=8, fontweight="bold"
        ),
    )
    draw_box(
        ax,
        (hx, hy + 0.2),
        (1.8, 0.6),
        "OrderEvent",
        BoxStyle(fill=GRAY4, fontsize=7.5),
    )
    draw_box(
        ax,
        (hx + 4.0, hy + 0.2),
        (2.0, 0.6),
        "PaymentEvent",
        BoxStyle(fill=GRAY4, fontsize=7.5),
    )
    draw_arrow(
        ax,
        (hx + 2.9, hy + 0.2),
        (hx + 0.9, hy + 0.2),
        ArrowCfg(
            lw=1.0,
            label="extends",
            label_offset=-0.3,
            label_fs=7,
        ),
    )
    draw_arrow(
        ax,
        (hx + 2.9, hy + 0.2),
        (hx + 5.0, hy + 0.2),
        ArrowCfg(
            lw=1.0,
            label="extends",
            label_offset=-0.3,
            label_fs=7,
        ),
    )

    ax.text(
        9.5,
        0.5,
        "Sub C subskrybuje bazowy Event\n"
        "\u2192 otrzymuje WSZYSTKIE podtypy",
        ha="center",
        va="center",
        fontsize=8.5,
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    save(fig, "pubsub_sub_type.png")


# ============================================================
# 4. Hierarchical / Wildcards subscription
# ============================================================
def draw_sub_hierarchical() -> None:
    """Draw sub hierarchical."""
    fig, ax = plt.subplots(1, 1, figsize=(FIG_W, 5.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Subskrypcja hierarchiczna (wildcards)"
        " \u2014 wzorce temat\u00f3w",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bold10 = BoxStyle(
        fill=GRAY2, fontsize=10, fontweight="bold"
    )
    draw_box(
        ax, (4.5, 5.8), (2.4, 0.8), "sensors/", bold10
    )

    fs9_g3 = BoxStyle(fill=GRAY3, fontsize=9)
    draw_box(
        ax,
        (1.5, 4.2),
        (2.4, 0.8),
        "temperature/",
        fs9_g3,
    )
    draw_box(
        ax,
        (7.5, 4.2),
        (2.4, 0.8),
        "humidity/",
        fs9_g3,
    )

    fs85_g4 = BoxStyle(fill=GRAY4, fontsize=8.5)
    draw_box(
        ax, (0.2, 2.8), (1.8, 0.7), "room1", fs85_g4
    )
    draw_box(
        ax, (2.4, 2.8), (1.8, 0.7), "room2", fs85_g4
    )
    draw_box(
        ax, (6.8, 2.8), (1.8, 0.7), "room1", fs85_g4
    )
    draw_box(
        ax, (9.0, 2.8), (1.8, 0.7), "room2", fs85_g4
    )

    thin = ArrowCfg(lw=1.0)
    draw_arrow(ax, (5.7, 5.8), (2.7, 5.0), thin)
    draw_arrow(ax, (5.7, 5.8), (8.7, 5.0), thin)
    draw_arrow(ax, (2.2, 4.2), (1.1, 3.5), thin)
    draw_arrow(ax, (3.2, 4.2), (3.3, 3.5), thin)
    draw_arrow(ax, (8.2, 4.2), (7.7, 3.5), thin)
    draw_arrow(ax, (9.2, 4.2), (9.9, 3.5), thin)

    ax.text(
        1.1,
        2.4,
        "sensors/temperature/room1",
        fontsize=7,
        ha="center",
        fontfamily="monospace",
        style="italic",
    )
    ax.text(
        3.3,
        2.4,
        "sensors/temperature/room2",
        fontsize=7,
        ha="center",
        fontfamily="monospace",
        style="italic",
    )

    ax.text(
        0.3,
        1.5,
        "Wzorce subskrypcji (MQTT-style):",
        fontsize=10,
        fontweight="bold",
    )

    patterns = [
        (
            '"sensors/temperature/room1"',
            "\u2192 TYLKO room1",
            "(dok\u0142adne dopasowanie)",
        ),
        (
            '"sensors/temperature/*"',
            "\u2192 room1, room2",
            "( * = jeden poziom)",
        ),
        (
            '"sensors/#"',
            "\u2192 WSZYSTKO",
            "( # = dowolna g\u0142\u0119boko\u015b\u0107)",
        ),
    ]
    for i, (pat, result, note) in enumerate(patterns):
        yy = 0.9 - i * 0.55
        ax.text(
            0.5,
            yy,
            pat,
            fontsize=9,
            fontweight="bold",
            fontfamily="monospace",
        )
        ax.text(
            7.0, yy, result, fontsize=9, fontweight="bold"
        )
        ax.text(
            9.5, yy, note, fontsize=8, style="italic"
        )

    save(fig, "pubsub_sub_hierarchical.png")


# ============================================================
# 5. At-most-once (QoS 0)
# ============================================================
def draw_qos_at_most_once() -> None:
    """Draw qos at most once."""
    fig, ax = plt.subplots(1, 1, figsize=(FIG_W, 4.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "QoS: At-most-once"
        " \u2014 \u201ewy\u015blij i zapomnij\u201d"
        " (0 lub 1 dostarczenie)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    px, bx, sx = 1.0, 4.8, 8.5
    pw, bw, sw = 2.0, 2.2, 2.0
    bh = 0.8
    bold10_g1 = BoxStyle(
        fill=GRAY1, fontsize=10, fontweight="bold"
    )
    bold10_g2 = BoxStyle(
        fill=GRAY2, fontsize=10, fontweight="bold"
    )
    draw_box(
        ax, (px, 5.0), (pw, bh), "Publisher", bold10_g1
    )
    draw_box(
        ax, (bx, 5.0), (bw, bh), "Broker", bold10_g2
    )
    draw_box(
        ax,
        (sx, 5.0),
        (sw, bh),
        "Subscriber",
        bold10_g1,
    )

    for xc in [px + pw / 2, bx + bw / 2, sx + sw / 2]:
        ax.plot(
            [xc, xc],
            [5.0, 1.2],
            color=GRAY3,
            lw=1,
            linestyle=":",
        )

    # Scenario A: success
    y = 4.3
    ax.text(
        0.2,
        y + 0.15,
        "Scenariusz A:",
        fontsize=8.5,
        fontweight="bold",
    )
    msg9 = ArrowCfg(label="MSG", label_fs=9)
    draw_arrow(
        ax, (px + pw / 2, y), (bx + bw / 2, y), msg9
    )
    draw_arrow(
        ax,
        (bx + bw / 2, y - 0.6),
        (sx + sw / 2, y - 0.6),
        msg9,
    )
    draw_check(ax, (sx + sw / 2 + 0.4, y - 0.6), size=0.18)
    ax.text(
        sx + sw / 2 + 0.7,
        y - 0.6,
        "OK",
        fontsize=9,
        fontweight="bold",
    )

    # Scenario B: lost
    y = 2.6
    ax.text(
        0.2,
        y + 0.15,
        "Scenariusz B:",
        fontsize=8.5,
        fontweight="bold",
    )
    draw_arrow(
        ax, (px + pw / 2, y), (bx + bw / 2, y), msg9
    )
    draw_dashed_arrow(
        ax, (bx + bw / 2, y - 0.6), (7.5, y - 0.6)
    )
    draw_cross(ax, (7.8, y - 0.6), size=0.2)
    ax.text(
        8.2,
        y - 0.55,
        "UTRACONA",
        fontsize=9,
        fontweight="bold",
    )
    ax.text(
        8.2,
        y - 1.0,
        "(brak retransmisji)",
        fontsize=8,
        style="italic",
    )

    ax.text(
        6.0,
        0.5,
        "Brak ACK, brak retransmisji."
        " Najszybszy. Use case:"
        " logi, metryki, telemetria.",
        ha="center",
        va="center",
        fontsize=9,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    save(fig, "pubsub_qos_at_most_once.png")


# ============================================================
# 6. At-least-once (QoS 1)
# ============================================================
def draw_qos_at_least_once() -> None:
    """Draw qos at least once."""
    fig, ax = plt.subplots(1, 1, figsize=(FIG_W, 5.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "QoS: At-least-once"
        " \u2014 \u201epowtarzaj a\u017c potwierdz\u0105\u201d"
        " (\u22651 dostarczenie)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bx, bw = 3.5, 2.2
    sx, sw = 8.0, 2.2
    bh = 0.8
    draw_box(
        ax,
        (bx, 5.5),
        (bw, bh),
        "Broker",
        BoxStyle(
            fill=GRAY2, fontsize=10, fontweight="bold"
        ),
    )
    draw_box(
        ax,
        (sx, 5.5),
        (sw, bh),
        "Subscriber",
        BoxStyle(
            fill=GRAY1, fontsize=10, fontweight="bold"
        ),
    )

    for xc in [bx + bw / 2, sx + sw / 2]:
        ax.plot(
            [xc, xc],
            [5.5, 0.8],
            color=GRAY3,
            lw=1,
            linestyle=":",
        )

    # Step 1: send MSG
    y1 = 4.8
    draw_arrow(
        ax,
        (bx + bw / 2, y1),
        (sx + sw / 2, y1),
        ArrowCfg(label="MSG #1", label_fs=9),
    )
    draw_check(ax, (sx + sw + 0.2, y1), size=0.15)
    ax.text(sx + sw + 0.5, y1, "odebrano", fontsize=8)

    # Step 2: ACK lost
    y2 = 3.9
    draw_dashed_arrow(
        ax,
        (sx + sw / 2, y2),
        (bx + bw + 1.2, y2),
    )
    ax.text(
        (bx + bw / 2 + sx + sw / 2) / 2,
        y2 + 0.18,
        "ACK",
        fontsize=9,
    )
    draw_cross(ax, (bx + bw + 0.8, y2), size=0.18)
    ax.text(
        bx + 0.3,
        y2 - 0.35,
        "ACK utracony!",
        fontsize=8.5,
        style="italic",
    )

    # Step 3: timeout -> retry
    y3 = 2.9
    ax.text(
        bx + bw / 2,
        y3 + 0.45,
        "timeout...",
        fontsize=8.5,
        style="italic",
        ha="center",
    )
    draw_arrow(
        ax,
        (bx + bw / 2, y3),
        (sx + sw / 2, y3),
        ArrowCfg(label="MSG #1 (retry)", label_fs=9),
    )
    draw_check(ax, (sx + sw + 0.2, y3), size=0.15)
    ax.text(
        sx + sw + 0.5,
        y3,
        "odebrano\n(ponownie!)",
        fontsize=8,
    )

    # Step 4: ACK ok
    y4 = 2.0
    draw_arrow(
        ax,
        (sx + sw / 2, y4),
        (bx + bw / 2, y4),
        ArrowCfg(label="ACK", label_fs=9),
    )
    draw_check(ax, (bx + bw / 2 - 0.5, y4), size=0.18)

    # Duplicate bracket
    ax.annotate(
        "",
        xy=(sx + sw + 1.3, y1),
        xytext=(sx + sw + 1.3, y3),
        arrowprops={
            "arrowstyle": "<->",
            "color": "black",
            "lw": 1.2,
        },
    )
    ax.text(
        sx + sw + 1.6,
        (y1 + y3) / 2,
        "DUPLIKAT!\nSubscriber\notrzyma\u0142 2x",
        fontsize=9,
        ha="left",
        va="center",
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    ax.text(
        6.0,
        0.5,
        "Broker czeka na ACK, retransmituje"
        " po timeout. Mog\u0105 by\u0107 duplikaty!\n"
        "Use case: zam\u00f3wienia, p\u0142atno\u015bci"
        " (subscriber musi by\u0107 idempotentny).",
        ha="center",
        va="center",
        fontsize=9,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    save(fig, "pubsub_qos_at_least_once.png")


# ============================================================
# 7. Exactly-once (QoS 2)
# ============================================================
def draw_qos_exactly_once() -> None:
    """Draw qos exactly once."""
    fig, ax = plt.subplots(1, 1, figsize=(FIG_W, 5.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "QoS: Exactly-once \u2014 4-krokowy"
        " handshake (dok\u0142adnie 1 dostarczenie)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bx, bw = 2.5, 2.2
    sx, sw = 7.5, 2.2
    bh = 0.8
    draw_box(
        ax,
        (bx, 6.0),
        (bw, bh),
        "Broker",
        BoxStyle(
            fill=GRAY2, fontsize=10, fontweight="bold"
        ),
    )
    draw_box(
        ax,
        (sx, 6.0),
        (sw, bh),
        "Subscriber",
        BoxStyle(
            fill=GRAY1, fontsize=10, fontweight="bold"
        ),
    )

    for xc in [bx + bw / 2, sx + sw / 2]:
        ax.plot(
            [xc, xc],
            [6.0, 1.0],
            color=GRAY3,
            lw=1,
            linestyle=":",
        )

    steps = [
        (
            5.2,
            "right",
            "PUBLISH  (msg_id=42)",
            "Broker wysy\u0142a wiadomo\u015b\u0107",
        ),
        (
            4.2,
            "left",
            "PUBREC  (otrzyma\u0142em id=42)",
            "Sub potwierdza odbi\u00f3r,"
            " zapisuje id",
        ),
        (
            3.2,
            "right",
            "PUBREL  (mo\u017cesz przetworzy\u0107)",
            "Broker zwalnia wiadomo\u015b\u0107",
        ),
        (
            2.2,
            "left",
            "PUBCOMP  (zako\u0144czone)",
            "Sub potwierdza przetworzenie",
        ),
    ]

    for i, (y, direction, label, desc) in enumerate(
        steps
    ):
        ax.text(
            bx + bw / 2 - 0.7,
            y,
            f"{i + 1}",
            fontsize=9,
            fontweight="bold",
            ha="center",
            va="center",
            bbox={
                "boxstyle": "circle,pad=0.18",
                "facecolor": GRAY3,
                "edgecolor": LN,
            },
        )

        if direction == "right":
            draw_arrow(
                ax,
                (bx + bw / 2, y),
                (sx + sw / 2, y),
                ArrowCfg(label=label, label_fs=9),
            )
        else:
            draw_arrow(
                ax,
                (sx + sw / 2, y),
                (bx + bw / 2, y),
                ArrowCfg(label=label, label_fs=9),
            )

        ax.text(
            sx + sw + 0.3,
            y,
            desc,
            fontsize=8,
            ha="left",
            va="center",
            style="italic",
        )

    ax.text(
        6.0,
        0.6,
        "Deduplikacja po msg_id."
        " Sub nie przetwarza przed PUBREL.\n"
        "Najkosztowniejszy (4 pakiety)."
        " Use case: transakcje finansowe,"
        " krytyczne zdarzenia.",
        ha="center",
        va="center",
        fontsize=9,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    save(fig, "pubsub_qos_exactly_once.png")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    logger.info(
        "Generating Pub/Sub diagrams"
        " (7 separate images)..."
    )
    draw_sub_topic()
    draw_sub_content()
    draw_sub_type()
    draw_sub_hierarchical()
    draw_qos_at_most_once()
    draw_qos_at_least_once()
    draw_qos_exactly_once()
    logger.info("Done!")

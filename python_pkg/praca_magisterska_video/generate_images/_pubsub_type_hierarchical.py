"""Subscription-type diagrams: type-based and hierarchical."""

from __future__ import annotations

from _pubsub_common import (
    FIG_W,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    ArrowCfg,
    BoxStyle,
    draw_arrow,
    draw_box,
    save,
)
import matplotlib.pyplot as plt


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
        "Subskrypcja type-based" " \u2014 routing po typie (klasie) obiektu",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bold10 = BoxStyle(fill=GRAY1, fontsize=10, fontweight="bold")
    draw_box(ax, (0.2, 4.2), (2.4, 1.1), "Publisher", bold10)

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
        BoxStyle(fill=GRAY2, fontsize=10, fontweight="bold"),
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
        ArrowCfg(label="oba (dziedziczenie!)", label_fs=8),
    )

    hx, hy = 0.5, 0.0
    draw_box(
        ax,
        (hx + 2.0, hy + 0.2),
        (1.8, 0.6),
        "Event",
        BoxStyle(fill=GRAY3, fontsize=8, fontweight="bold"),
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
        "Sub C subskrybuje bazowy Event\n" "\u2192 otrzymuje WSZYSTKIE podtypy",
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
        "Subskrypcja hierarchiczna (wildcards)" " \u2014 wzorce temat\u00f3w",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bold10 = BoxStyle(fill=GRAY2, fontsize=10, fontweight="bold")
    draw_box(ax, (4.5, 5.8), (2.4, 0.8), "sensors/", bold10)

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
    draw_box(ax, (0.2, 2.8), (1.8, 0.7), "room1", fs85_g4)
    draw_box(ax, (2.4, 2.8), (1.8, 0.7), "room2", fs85_g4)
    draw_box(ax, (6.8, 2.8), (1.8, 0.7), "room1", fs85_g4)
    draw_box(ax, (9.0, 2.8), (1.8, 0.7), "room2", fs85_g4)

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
        ax.text(7.0, yy, result, fontsize=9, fontweight="bold")
        ax.text(9.5, yy, note, fontsize=8, style="italic")

    save(fig, "pubsub_sub_hierarchical.png")

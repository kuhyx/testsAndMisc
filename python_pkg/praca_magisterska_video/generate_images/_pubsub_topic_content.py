"""Subscription-type diagrams: topic-based and content-based."""

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
    DashedCfg,
    draw_arrow,
    draw_box,
    draw_dashed_arrow,
    save,
)
import matplotlib.pyplot as plt


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
        "Subskrypcja topic-based" " \u2014 routing po nazwie tematu",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=12,
    )

    bold10 = BoxStyle(fill=GRAY1, fontsize=10, fontweight="bold")
    fs85 = BoxStyle(fill=GRAY1, fontsize=8.5)

    draw_box(ax, (0.2, 3.2), (2.4, 1.1), "Publisher", bold10)
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
        BoxStyle(fill=GRAY2, fontsize=10, fontweight="bold"),
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

    bold10 = BoxStyle(fill=GRAY1, fontsize=10, fontweight="bold")
    draw_box(ax, (0.2, 3.5), (2.4, 1.1), "Publisher", bold10)
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
        "BROKER\n\newaluuje filtry\n" "ka\u017cdego subscribera",
        BoxStyle(fill=GRAY2, fontsize=9, fontweight="bold"),
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
            label='"book" \u2260 "food"' "  \u2717  odrzucono",
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

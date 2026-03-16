"""QoS delivery guarantee diagrams: at-most-once, at-least-once, exactly-once."""

from __future__ import annotations

from _pubsub_common import (
    FIG_W,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    ArrowCfg,
    BoxStyle,
    draw_arrow,
    draw_box,
    draw_check,
    draw_cross,
    draw_dashed_arrow,
    save,
)
import matplotlib.pyplot as plt


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
    bold10_g1 = BoxStyle(fill=GRAY1, fontsize=10, fontweight="bold")
    bold10_g2 = BoxStyle(fill=GRAY2, fontsize=10, fontweight="bold")
    draw_box(ax, (px, 5.0), (pw, bh), "Publisher", bold10_g1)
    draw_box(ax, (bx, 5.0), (bw, bh), "Broker", bold10_g2)
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
    draw_arrow(ax, (px + pw / 2, y), (bx + bw / 2, y), msg9)
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
    draw_arrow(ax, (px + pw / 2, y), (bx + bw / 2, y), msg9)
    draw_dashed_arrow(ax, (bx + bw / 2, y - 0.6), (7.5, y - 0.6))
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
        BoxStyle(fill=GRAY2, fontsize=10, fontweight="bold"),
    )
    draw_box(
        ax,
        (sx, 5.5),
        (sw, bh),
        "Subscriber",
        BoxStyle(fill=GRAY1, fontsize=10, fontweight="bold"),
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
        BoxStyle(fill=GRAY2, fontsize=10, fontweight="bold"),
    )
    draw_box(
        ax,
        (sx, 6.0),
        (sw, bh),
        "Subscriber",
        BoxStyle(fill=GRAY1, fontsize=10, fontweight="bold"),
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
            "Sub potwierdza odbi\u00f3r," " zapisuje id",
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

    for i, (y, direction, label, desc) in enumerate(steps):
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

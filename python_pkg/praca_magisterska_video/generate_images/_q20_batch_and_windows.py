"""Batch vs streaming concept and window type diagrams for Q20."""

from __future__ import annotations

from typing import TYPE_CHECKING

from _q20_common import (
    FS,
    FS_LABEL,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    draw_arrow,
    draw_box,
    plt,
    save_fig,
)
import matplotlib.patches as mpatches

if TYPE_CHECKING:
    from matplotlib.axes import Axes


# ============================================================
# 1. Batch vs Streaming concept
# ============================================================
def gen_batch_vs_streaming() -> None:
    """Gen batch vs streaming."""
    fig, axes = plt.subplots(2, 1, figsize=(9, 5))
    fig.suptitle(
        "Batch vs Streaming — dwa modele przetwarzania",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    # Batch
    ax = axes[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("BATCH (wsadowe)", fontsize=FS_LABEL, fontweight="bold")

    # Data collected
    draw_box(
        ax,
        0.5,
        0.8,
        3.0,
        1.4,
        "Zbierz WSZYSTKIE\ndane\n(godziny / dni)",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 3.5, 1.5, 4.5, 1.5, lw=2)
    draw_box(
        ax,
        4.5,
        0.8,
        2.5,
        1.4,
        "Analiza\n(batch job)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 7.0, 1.5, 8.0, 1.5, lw=2)
    draw_box(
        ax,
        8.0,
        0.8,
        2.5,
        1.4,
        "Wynik\n(jednorazowy)",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    ax.text(11.0, 1.5, "min-h", fontsize=FS, va="center", fontweight="bold")

    # Streaming
    ax = axes[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title("STREAMING (strumieniowe)", fontsize=FS_LABEL, fontweight="bold")

    # Events flowing
    events_x = [0.5, 1.5, 2.5, 3.5]
    for i, ex in enumerate(events_x):
        draw_box(
            ax,
            ex,
            1.0,
            0.8,
            0.8,
            f"e{i + 1}",
            fill=GRAY4,
            fontsize=FS,
            fontweight="bold",
            rounded=False,
        )
        if i < len(events_x) - 1:
            draw_arrow(ax, ex + 0.8, 1.4, ex + 1.0, 1.4, lw=1)

    ax.text(4.8, 1.4, "...", fontsize=FS_LABEL, va="center")
    draw_arrow(ax, 5.2, 1.4, 5.8, 1.4, lw=2)

    draw_box(
        ax,
        5.8,
        0.8,
        2.8,
        1.4,
        "Analiza\nCIĄGŁA\n(event-by-event)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 8.6, 1.5, 9.3, 1.5, lw=2)
    draw_box(
        ax,
        9.3,
        0.8,
        2.0,
        1.4,
        "Wyniki\nciągłe",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    ax.text(11.5, 0.5, "ms-s", fontsize=FS, va="center", fontweight="bold")

    # Arrow marking infinity
    ax.annotate(
        "",
        xy=(0.2, 1.4),
        xytext=(-0.3, 1.4),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(0.0, 2.3, "∞ zdarzeń", fontsize=FS_SMALL, ha="center", style="italic")

    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_fig(fig, "q20_batch_vs_streaming.png")


# ============================================================
# 2. All 4 window types (TSSG)
# ============================================================
def _draw_tumbling_window(ax: Axes, events: list[int]) -> None:
    """Draw tumbling window section."""
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Tumbling Window (okno przerzutne) — rozłączne, stały rozmiar",
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    # Time axis
    ax.annotate(
        "",
        xy=(13.5, 1.0),
        xytext=(0.3, 1.0),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(13.5, 0.6, "czas", fontsize=FS_SMALL, ha="center")

    # Events
    for i, e in enumerate(events):
        x = 1.0 + i * 1.0
        ax.plot(x, 1.0, "ko", markersize=5)
        ax.text(x, 0.5, f"e{e}", fontsize=FS_SMALL, ha="center")

    # Windows
    colors_w = [GRAY1, GRAY3, GRAY1, GRAY3]
    for w in range(4):
        x_start = 1.0 + w * 3.0 - 0.3
        rect = mpatches.FancyBboxPatch(
            (x_start, 1.5),
            3.0,
            1.2,
            boxstyle="round,pad=0.1",
            facecolor=colors_w[w],
            edgecolor=LN,
            lw=1.5,
        )
        ax.add_patch(rect)
        ax.text(
            x_start + 1.5,
            2.1,
            f"Okno {w + 1}",
            fontsize=FS,
            ha="center",
            fontweight="bold",
        )
        # Braces down to events
        for j in range(3):
            ex = 1.0 + w * 3.0 + j * 1.0
            ax.plot([ex, ex], [1.0, 1.5], color=LN, lw=0.8, linestyle="--")

    ax.text(
        7.0,
        3.2,
        "Każde zdarzenie → DOKŁADNIE 1 okno. Zero nakładania.",
        fontsize=FS,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )


def _draw_sliding_window(ax: Axes, events: list[int]) -> None:
    """Draw sliding window section."""
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Sliding Window (okno przesuwne) — nakładające, stały rozmiar + krok",
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    ax.annotate(
        "",
        xy=(13.5, 1.0),
        xytext=(0.3, 1.0),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(13.5, 0.6, "czas", fontsize=FS_SMALL, ha="center")

    for i, e in enumerate(events[:8]):
        x = 1.0 + i * 1.0
        ax.plot(x, 1.0, "ko", markersize=5)
        ax.text(x, 0.5, f"e{e}", fontsize=FS_SMALL, ha="center")

    # Sliding windows: size=4, slide=2
    slide_colors = [GRAY1, GRAY2, GRAY3]
    for w in range(3):
        x_start = 0.7 + w * 2.0
        y_base = 1.5 + w * 0.9
        rect = mpatches.FancyBboxPatch(
            (x_start, y_base),
            4.0,
            0.7,
            boxstyle="round,pad=0.08",
            facecolor=slide_colors[w],
            edgecolor=LN,
            lw=1.5,
            alpha=0.7,
        )
        ax.add_patch(rect)
        ax.text(
            x_start + 2.0,
            y_base + 0.35,
            f"Okno {w + 1} (size=4)",
            fontsize=FS_SMALL,
            ha="center",
            fontweight="bold",
        )

    ax.text(
        10.5,
        3.5,
        "krok=2\nNakładanie!\ne3,e4 → w oknie 1 i 2",
        fontsize=FS,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )


def _draw_session_window(ax: Axes) -> None:
    """Draw session window section."""
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Session Window (okno sesji) — dynamiczny rozmiar, gap = przerwa",
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    ax.annotate(
        "",
        xy=(13.5, 1.0),
        xytext=(0.3, 1.0),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(13.5, 0.6, "czas", fontsize=FS_SMALL, ha="center")

    # Cluster 1: events close together
    cluster1 = [1.0, 1.8, 2.3, 3.0]
    for x in cluster1:
        ax.plot(x, 1.0, "ko", markersize=5)

    # Gap
    ax.annotate(
        "",
        xy=(7.0, 0.7),
        xytext=(4.0, 0.7),
        arrowprops={"arrowstyle": "<->", "lw": 1, "color": LN},
    )
    ax.text(
        5.5,
        0.3,
        "GAP > timeout",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        style="italic",
    )

    # Cluster 2
    cluster2 = [8.0, 8.8, 9.5]
    for x in cluster2:
        ax.plot(x, 1.0, "ko", markersize=5)

    # Session boxes
    rect1 = mpatches.FancyBboxPatch(
        (0.7, 1.4),
        2.6,
        1.0,
        boxstyle="round,pad=0.1",
        facecolor=GRAY1,
        edgecolor=LN,
        lw=1.5,
    )
    ax.add_patch(rect1)
    ax.text(
        2.0, 1.9, "Sesja 1\n(4 zdarzenia)", fontsize=FS, ha="center", fontweight="bold"
    )

    rect2 = mpatches.FancyBboxPatch(
        (7.7, 1.4),
        2.1,
        1.0,
        boxstyle="round,pad=0.1",
        facecolor=GRAY3,
        edgecolor=LN,
        lw=1.5,
    )
    ax.add_patch(rect2)
    ax.text(
        8.75, 1.9, "Sesja 2\n(3 zdarzenia)", fontsize=FS, ha="center", fontweight="bold"
    )

    ax.text(
        5.5,
        3.0,
        "Nowa sesja po przerwie > gap",
        fontsize=FS,
        ha="center",
        style="italic",
    )


def _draw_global_window(ax: Axes) -> None:
    """Draw global window section."""
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Global Window — jedno okno na cały strumień + trigger",
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    ax.annotate(
        "",
        xy=(13.5, 1.0),
        xytext=(0.3, 1.0),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": LN},
    )
    ax.text(13.5, 0.6, "czas", fontsize=FS_SMALL, ha="center")

    for i in range(12):
        x = 1.0 + i * 1.0
        ax.plot(x, 1.0, "ko", markersize=5)

    # One big window
    rect = mpatches.FancyBboxPatch(
        (0.5, 1.4),
        12.5,
        1.0,
        boxstyle="round,pad=0.1",
        facecolor=GRAY1,
        edgecolor=LN,
        lw=2,
    )
    ax.add_patch(rect)
    ax.text(
        6.75,
        1.9,
        "GLOBAL WINDOW (cały strumień)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
    )

    # Trigger markers
    for tx in [4.0, 8.0, 12.0]:
        ax.plot([tx, tx], [1.4, 2.4], color=LN, lw=2, linestyle="--")
        ax.text(
            tx,
            2.7,
            "EMIT",
            fontsize=FS_SMALL,
            ha="center",
            fontweight="bold",
            bbox={"boxstyle": "round,pad=0.1", "facecolor": GRAY3, "edgecolor": LN},
        )

    ax.text(
        6.75,
        3.3,
        "Trigger decyduje kiedy emitować (np. co N zdarzeń)",
        fontsize=FS,
        ha="center",
        style="italic",
    )


def gen_window_types() -> None:
    """Gen window types."""
    fig, axes = plt.subplots(4, 1, figsize=(9, 10))
    fig.suptitle("4 typy okien — TSSG", fontsize=FS_TITLE, fontweight="bold")

    events = list(range(1, 13))

    _draw_tumbling_window(axes[0], events)
    _draw_sliding_window(axes[1], events)
    _draw_session_window(axes[2])
    _draw_global_window(axes[3])

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_fig(fig, "q20_window_types.png")

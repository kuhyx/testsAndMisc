"""Late data strategies and decision tree diagrams for Q20."""

from __future__ import annotations

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
    draw_arrow,
    draw_box,
    plt,
    save_fig,
)


# ============================================================
# 16. Late data strategies (DRAS)
# ============================================================
def gen_late_data_strategies() -> None:
    """Gen late data strategies."""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Late Data — 4 strategie (mnemonik DRAS)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Setup: window closed, late event arrives
    draw_box(
        ax,
        0.5,
        5.5,
        4.5,
        1.0,
        "Okno [14:00-14:05]\nZAMKNIĘTE o 14:05",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )
    draw_box(
        ax,
        6.0,
        5.5,
        4.5,
        1.0,
        "Spóźnione zdarzenie\nevent_time=14:00:03\narrives=14:05:30",
        fill="#F8D7DA",
        fontsize=FS_SMALL,
        fontweight="bold",
    )
    draw_arrow(ax, 10.5, 6.0, 5.0, 6.0, lw=2, color="#C62828", style="->")
    ax.text(
        7.5,
        5.2,
        "LATE!",
        fontsize=FS_LABEL,
        ha="center",
        fontweight="bold",
        color="#C62828",
    )

    # 4 strategies
    strategies = [
        ("D — Drop", "Odrzuć spóźnione", "/dev/null", GRAY4),
        ("R — Recompute", "Przelicz okno ponownie", "poprawne ale kosztowne", GRAY1),
        (
            "A — Allowed lateness",
            "Czekaj dodatkowy czas\n(np. +2 min)",
            "kompromis pamięci",
            GRAY2,
        ),
        (
            "S — Side output",
            "Przekieruj do osobnej\nkolejki",
            "elastyczne, ręczna analiza",
            GRAY3,
        ),
    ]
    for i, (name, desc, tradeoff, color) in enumerate(strategies):
        y = 3.8 - i * 1.1
        draw_box(ax, 0.5, y, 2.5, 0.9, name, fill=color, fontsize=FS, fontweight="bold")
        ax.text(3.3, y + 0.45, desc, fontsize=FS_SMALL, va="center")
        ax.text(
            8.5,
            y + 0.45,
            tradeoff,
            fontsize=FS_SMALL,
            va="center",
            style="italic",
            color="#555",
        )

    save_fig(fig, "q20_late_data_strategies.png")


# ============================================================
# 17. Decision tree — which platform
# ============================================================
def gen_decision_tree() -> None:
    """Gen decision tree."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Drzewo decyzyjne — wybór platformy",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Root question
    draw_box(
        ax,
        3.5,
        5.5,
        4.5,
        1.0,
        "Latencja < 10ms\nwymagana?",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # TAK branch
    draw_arrow(ax, 3.5, 5.7, 2.0, 5.0, lw=1.5)
    ax.text(2.3, 5.3, "TAK", fontsize=FS, fontweight="bold")

    draw_box(
        ax,
        0.3,
        3.5,
        3.5,
        1.0,
        "Dane już w Kafce?\nProste transformacje?",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )

    # TAK → Kafka Streams
    draw_arrow(ax, 0.3, 3.7, -0.1, 3.0, lw=1.5)
    ax.text(0.0, 3.3, "TAK", fontsize=FS_SMALL, fontweight="bold")
    draw_box(
        ax,
        -0.3,
        1.8,
        2.5,
        1.0,
        "Kafka\nStreams",
        fill=GRAY5,
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    # NIE → Flink
    draw_arrow(ax, 3.8, 3.7, 4.5, 3.0, lw=1.5)
    ax.text(4.0, 3.3, "NIE\n(złożona logika)", fontsize=FS_SMALL)
    draw_box(
        ax,
        3.0,
        1.8,
        2.5,
        1.0,
        "Apache\nFlink",
        fill=GRAY5,
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    # NIE branch
    draw_arrow(ax, 8.0, 5.7, 9.5, 5.0, lw=1.5)
    ax.text(8.7, 5.3, "NIE", fontsize=FS, fontweight="bold")

    draw_box(
        ax,
        7.5,
        3.5,
        4.2,
        1.0,
        "~100ms-1s OK?\nPotrzeba ML / SQL?",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )

    # TAK + ML → Spark
    draw_arrow(ax, 9.5, 3.5, 9.5, 3.0, lw=1.5)
    ax.text(10.0, 3.3, "TAK + ML/SQL", fontsize=FS_SMALL)
    draw_box(
        ax,
        8.0,
        1.8,
        2.5,
        1.0,
        "Spark\nStreaming",
        fill=GRAY5,
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    # TAK + proste → Kafka Streams too
    draw_arrow(ax, 7.5, 3.7, 6.5, 3.0, lw=1.5)
    ax.text(6.3, 3.3, "proste + TAK", fontsize=FS_SMALL)
    draw_box(
        ax,
        5.8,
        1.8,
        2.0,
        1.0,
        "Kafka\nStreams",
        fill=GRAY5,
        fontsize=FS,
        fontweight="bold",
    )

    # Legend
    ax.text(
        6.0,
        0.7,
        "Reguła: Kafka Streams = najprostsze (library) | "
        "Flink = najpotężniejszy (true streaming) | Spark = ekosystem ML",
        fontsize=FS,
        ha="center",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    save_fig(fig, "q20_decision_tree.png")

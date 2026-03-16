"""Spark Streaming, Lambda/Kappa architecture, and exactly-once diagrams for Q20."""

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
    LN,
    draw_arrow,
    draw_box,
    draw_table,
    plt,
    save_fig,
)


# ============================================================
# 12. Spark Streaming architecture
# ============================================================
def gen_spark_streaming_arch() -> None:
    """Gen spark streaming arch."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Spark Streaming — architektura (micro-batch)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Cluster border
    draw_box(ax, 0.3, 0.5, 11.4, 5.8, "", fill=GRAY4, rounded=True, lw=2.5)
    ax.text(
        6.0, 6.0, "SPARK CLUSTER", fontsize=FS_LABEL, ha="center", fontweight="bold"
    )

    # Driver
    draw_box(
        ax,
        1.0,
        4.5,
        3.0,
        1.2,
        "Driver\n(planuje mini-batche)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    draw_arrow(ax, 2.5, 4.5, 6.0, 4.0, lw=1.5)

    # Batches
    batches = ["batch 1\n(e1,e2,e3)", "batch 2\n(e4,e5,e6)", "batch 3\n(e7,e8,e9)"]
    for i, b in enumerate(batches):
        y = 2.8 - i * 1.0
        draw_box(
            ax, 4.5, y, 2.5, 0.8, b, fill=GRAY1, fontsize=FS_SMALL, fontweight="bold"
        )
        # map → reduce
        draw_arrow(ax, 7.0, y + 0.4, 7.5, y + 0.4, lw=1)
        draw_box(ax, 7.5, y, 1.3, 0.8, "map→\nreduce", fill=GRAY3, fontsize=5.5)
        draw_arrow(ax, 8.8, y + 0.4, 9.3, y + 0.4, lw=1)
        draw_box(
            ax, 9.3, y, 1.5, 0.8, f"result {i + 1}", fill="white", fontsize=FS_SMALL
        )

    # Spark ecosystem
    draw_box(
        ax,
        1.0,
        1.0,
        3.0,
        1.0,
        "Spark SQL / MLlib\n(ten sam ekosystem!)",
        fill=GRAY5,
        fontsize=FS,
        fontweight="bold",
    )

    ax.text(
        6.0,
        0.3,
        "ZALETA: batch API    |    WADA: latencja ≥ batch interval (~100ms)",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": LN},
    )

    save_fig(fig, "q20_spark_streaming_arch.png")


# ============================================================
# 13. Lambda vs Kappa architecture
# ============================================================
def gen_lambda_vs_kappa() -> None:
    """Gen lambda vs kappa."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 7))
    fig.suptitle("Architektura Lambda vs Kappa", fontsize=FS_TITLE, fontweight="bold")

    # --- Lambda ---
    ax = axes[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "LAMBDA — 2 ścieżki (batch + speed)", fontsize=FS_LABEL, fontweight="bold"
    )

    # Source
    draw_box(
        ax,
        0.3,
        1.8,
        2.0,
        1.5,
        "Źródło\ndanych",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # Batch layer (top)
    draw_box(
        ax,
        3.5,
        3.3,
        3.0,
        1.2,
        "Batch Layer\n(Spark)\nprzelicza co godzinę",
        fill=GRAY1,
        fontsize=FS_SMALL,
        fontweight="bold",
    )
    draw_arrow(ax, 2.3, 3.0, 3.5, 3.9, lw=1.5)

    # Speed layer (bottom)
    draw_box(
        ax,
        3.5,
        0.8,
        3.0,
        1.2,
        "Speed Layer\n(Flink)\nreal-time",
        fill=GRAY3,
        fontsize=FS_SMALL,
        fontweight="bold",
    )
    draw_arrow(ax, 2.3, 2.2, 3.5, 1.4, lw=1.5)

    # Results
    draw_box(
        ax,
        7.5,
        3.3,
        2.0,
        1.2,
        "Dokładne\nwyniki\n(wolne)",
        fill=GRAY4,
        fontsize=FS_SMALL,
    )
    draw_arrow(ax, 6.5, 3.9, 7.5, 3.9, lw=1.5)

    draw_box(
        ax,
        7.5,
        0.8,
        2.0,
        1.2,
        "Przybliżone\nwyniki\n(szybkie)",
        fill=GRAY4,
        fontsize=FS_SMALL,
    )
    draw_arrow(ax, 6.5, 1.4, 7.5, 1.4, lw=1.5)

    # Merge
    draw_box(
        ax,
        10.0,
        2.0,
        1.5,
        1.5,
        "MERGE\n→ UI",
        fill=GRAY5,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 9.5, 3.5, 10.0, 3.0, lw=1.5)
    draw_arrow(ax, 9.5, 1.8, 10.0, 2.5, lw=1.5)

    ax.text(
        6.0,
        0.1,
        "2 systemy, 2 kody — złożone ale pewne",
        fontsize=FS,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    # --- Kappa ---
    ax = axes[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "KAPPA — 1 ścieżka (streaming only)", fontsize=FS_LABEL, fontweight="bold"
    )

    # Source
    draw_box(
        ax,
        0.3,
        1.3,
        2.0,
        1.5,
        "Źródło\ndanych",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # Single streaming layer
    draw_box(
        ax,
        3.5,
        1.3,
        3.5,
        1.5,
        "Streaming Layer\n(Flink)\n+ replay z Kafka log",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 2.3, 2.05, 3.5, 2.05, lw=2)

    # Output
    draw_box(
        ax,
        8.0,
        1.3,
        2.5,
        1.5,
        "Wyniki\n→ UI",
        fill=GRAY4,
        fontsize=FS,
        fontweight="bold",
    )
    draw_arrow(ax, 7.0, 2.05, 8.0, 2.05, lw=2)

    # Replay arrow
    ax.annotate(
        "",
        xy=(3.5, 1.0),
        xytext=(7.0, 1.0),
        arrowprops={
            "arrowstyle": "<-",
            "lw": 1.5,
            "color": LN,
            "connectionstyle": "arc3,rad=0.3",
            "linestyle": "--",
        },
    )
    ax.text(
        5.25,
        0.3,
        "Replay z Kafka\n(przetwórz historię od nowa)",
        fontsize=FS_SMALL,
        ha="center",
        style="italic",
    )

    ax.text(
        6.0,
        3.3,
        "1 system, 1 kod — prostsze, ale replay = dużo I/O",
        fontsize=FS,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_fig(fig, "q20_lambda_vs_kappa.png")


# ============================================================
# 14. Lambda vs Kappa comparison table
# ============================================================
def gen_lambda_kappa_table() -> None:
    """Gen lambda kappa table."""
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(-4.5, 1)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Lambda vs Kappa — porównanie", fontsize=FS_TITLE, fontweight="bold", pad=10
    )

    headers = ["Cecha", "Lambda", "Kappa"]
    col_w = [2.5, 3.5, 3.5]
    rows = [
        ["Ścieżki", "2 (batch + speed)", "1 (streaming)"],
        ["Kod", "2 implementacje", "1 implementacja"],
        ["Złożoność", "wysoka", "niska"],
        ["Replay", "batch przelicza", "Kafka replay"],
        ["Spójność", "merge wymagany", "natywna"],
        ["Przykład", "Netflix, LinkedIn", "Uber, Confluent"],
    ]
    draw_table(
        ax, headers, rows, x0=0.25, y0=0.5, col_widths=col_w, row_h=0.55, fontsize=7.5
    )

    save_fig(fig, "q20_lambda_kappa_table.png")


# ============================================================
# 15. Exactly-once comparison
# ============================================================
def gen_exactly_once() -> None:
    """Gen exactly once."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Exactly-Once — mechanizmy na 3 platformach",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Flink
    draw_box(ax, 0.3, 4.3, 11.0, 2.0, "", fill=GRAY4, rounded=True, lw=1.5)
    ax.text(
        1.0,
        5.9,
        "Flink — Distributed Snapshots (Chandy-Lamport)",
        fontsize=FS,
        fontweight="bold",
    )

    flink_steps = ["source", "|B|", "map()", "|B|", "sink()"]
    bx = 1.0
    for s in flink_steps:
        if s == "|B|":
            ax.text(
                bx + 0.25,
                4.85,
                s,
                fontsize=FS,
                ha="center",
                fontweight="bold",
                bbox={"boxstyle": "round,pad=0.1", "facecolor": GRAY5, "edgecolor": LN},
            )
            draw_arrow(ax, bx - 0.1, 4.85, bx + 0.05, 4.85, lw=1)
            bx += 0.7
        else:
            draw_box(
                ax,
                bx,
                4.6,
                1.5,
                0.55,
                s,
                fill=GRAY1,
                fontsize=FS_SMALL,
                fontweight="bold",
            )
            bx += 1.8
    ax.text(
        8.5,
        5.0,
        "barrier → save state\n→ checkpoint (HDFS/S3)",
        fontsize=FS_SMALL,
        style="italic",
    )

    # Kafka Streams
    draw_box(ax, 0.3, 2.3, 11.0, 1.5, "", fill=GRAY1, rounded=True, lw=1.5)
    ax.text(
        1.0, 3.5, "Kafka Streams — Transakcje Kafka", fontsize=FS, fontweight="bold"
    )
    ax.text(
        1.5,
        2.85,
        "idempotent producer + begin TX → produce → commit TX → consumer offsets w TX",
        fontsize=FS_SMALL,
    )

    # Spark
    draw_box(ax, 0.3, 0.5, 11.0, 1.5, "", fill=GRAY3, rounded=True, lw=1.5)
    ax.text(
        1.0,
        1.7,
        "Spark Streaming — Write-Ahead Log (WAL)",
        fontsize=FS,
        fontweight="bold",
    )
    ax.text(
        1.5,
        1.05,
        "WAL + checkpointing micro-batchów + idempotent sinks (np. upsert do DB)",
        fontsize=FS_SMALL,
    )

    save_fig(fig, "q20_exactly_once.png")

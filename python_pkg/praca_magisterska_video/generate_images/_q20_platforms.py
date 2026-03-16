"""Streaming ecosystem, micro-batch, platform comparison, and engine diagrams for Q20."""

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
# 7. Streaming ecosystem overview
# ============================================================
def gen_streaming_ecosystem() -> None:
    """Gen streaming ecosystem."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Ekosystem przetwarzania strumieniowego",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Source
    draw_box(
        ax,
        0.3,
        2.5,
        2.0,
        3.0,
        "Kafka\nTopics\n(źródło)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # Engines
    engines = [
        ("Kafka Streams\n(library w JVM)", GRAY1, 4.7),
        ("Apache Flink\n(klaster)", GRAY3, 3.2),
        ("Spark Streaming\n(klaster)", GRAY5, 1.7),
    ]
    for label, color, y in engines:
        draw_box(
            ax, 4.0, y, 3.0, 1.2, label, fill=color, fontsize=FS, fontweight="bold"
        )
        draw_arrow(ax, 2.3, 4.0, 4.0, y + 0.6, lw=1.5)

    # Sinks
    sinks = [
        ("Kafka topic\n/ baza danych", GRAY4, 4.7),
        ("DB / Kafka\n/ S3", GRAY4, 3.2),
        ("HDFS / DB\n/ dashboard", GRAY4, 1.7),
    ]
    for label, color, y in sinks:
        draw_box(ax, 8.5, y, 2.5, 1.2, label, fill=color, fontsize=FS)
        draw_arrow(ax, 7.0, y + 0.6, 8.5, y + 0.6, lw=1.5)

    # Labels
    ax.text(1.3, 6.0, "ŹRÓDŁO", fontsize=FS_LABEL, ha="center", fontweight="bold")
    ax.text(5.5, 6.2, "SILNIK", fontsize=FS_LABEL, ha="center", fontweight="bold")
    ax.text(9.75, 6.2, "WYNIK", fontsize=FS_LABEL, ha="center", fontweight="bold")

    # Latency annotations
    ax.text(5.5, 5.95, "~1-10 ms", fontsize=FS_SMALL, ha="center", style="italic")
    ax.text(5.5, 4.5, "<10 ms", fontsize=FS_SMALL, ha="center", style="italic")
    ax.text(5.5, 3.0, "~100 ms", fontsize=FS_SMALL, ha="center", style="italic")

    save_fig(fig, "q20_streaming_ecosystem.png")


# ============================================================
# 8. True streaming vs Micro-batch
# ============================================================
def gen_true_vs_microbatch() -> None:
    """Gen true vs microbatch."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.5))
    fig.suptitle("True Streaming vs Micro-Batch", fontsize=FS_TITLE, fontweight="bold")

    # True streaming
    ax = axes[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "TRUE STREAMING (Flink, Kafka Streams) — event-by-event",
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    for i in range(6):
        x = 1.0 + i * 1.8
        # Event
        draw_box(
            ax,
            x,
            2.0,
            0.8,
            0.7,
            f"e{i + 1}",
            fill=GRAY1,
            fontsize=FS,
            fontweight="bold",
            rounded=False,
        )
        # Arrow down
        draw_arrow(ax, x + 0.4, 2.0, x + 0.4, 1.4, lw=1)
        # Result
        draw_box(
            ax,
            x,
            0.5,
            0.8,
            0.7,
            f"r{i + 1}",
            fill=GRAY3,
            fontsize=FS,
            fontweight="bold",
            rounded=False,
        )
        # Latency label
        ax.text(x + 0.4, 1.6, "~ms", fontsize=5, ha="center", color="#555")

    ax.text(
        11.5,
        1.3,
        "Latencja:\n< 10 ms",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    # Micro-batch
    ax = axes[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.5)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "MICRO-BATCH (Spark Streaming) — grupami co ~100ms",
        fontsize=FS_LABEL,
        fontweight="bold",
    )

    batch_colors = [GRAY1, GRAY2, GRAY3]
    for b in range(3):
        bx = 0.8 + b * 3.5
        # Batch boundary
        draw_box(ax, bx, 1.8, 3.0, 1.0, "", fill=batch_colors[b], rounded=True, lw=1.5)
        ax.text(
            bx + 1.5, 2.6, f"Batch {b + 1}", fontsize=FS, ha="center", fontweight="bold"
        )
        for j in range(3):
            ex = bx + 0.3 + j * 0.9
            draw_box(
                ax,
                ex,
                2.0,
                0.7,
                0.5,
                f"e{b * 3 + j + 1}",
                fill="white",
                fontsize=FS_SMALL,
                rounded=False,
            )

        # Arrow down
        draw_arrow(ax, bx + 1.5, 1.8, bx + 1.5, 1.2, lw=1.5)
        # Result
        draw_box(
            ax,
            bx + 0.5,
            0.4,
            2.0,
            0.7,
            f"result {b + 1}",
            fill=GRAY4,
            fontsize=FS,
            fontweight="bold",
        )

    ax.text(
        11.5,
        1.3,
        "Latencja:\n~100ms-s",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )

    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_fig(fig, "q20_true_vs_microbatch.png")


# ============================================================
# 9. Platform comparison table
# ============================================================
def gen_platform_comparison() -> None:
    """Gen platform comparison."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(0, 11.5)
    ax.set_ylim(-6, 1)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Porównanie platform strumieniowych",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    headers = ["Cecha", "Kafka Streams", "Apache Flink", "Spark Streaming"]
    col_w = [2.5, 2.8, 2.8, 2.8]
    rows = [
        ["Model", "event-by-event", "event-by-event", "micro-batch (~100ms)"],
        ["Deployment", "library (w JVM)", "klaster", "klaster"],
        ["Latencja", "~1-10 ms", "< 10 ms", "100 ms - sekundy"],
        ["Exactly-once", "Kafka TXN", "checkpointing", "WAL"],
        ["State", "RocksDB local", "RocksDB + ckpt", "in-memory / ext"],
        ["Okna", "T, S, Session", "wszystkie + custom", "T, S"],
        ["Use case", "Kafka → Kafka", "złożona analityka", "ETL + ML / SQL"],
    ]
    draw_table(
        ax,
        headers,
        rows,
        x0=0.25,
        y0=0.5,
        col_widths=col_w,
        row_h=0.6,
        fontsize=7,
        header_fontsize=8,
    )

    save_fig(fig, "q20_platform_comparison.png")


# ============================================================
# 10. Kafka Streams architecture
# ============================================================
def gen_kafka_streams_arch() -> None:
    """Gen kafka streams arch."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Kafka Streams — architektura (library w JVM)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Outer box: Your Java application
    draw_box(ax, 0.5, 0.5, 11.0, 5.5, "", fill=GRAY4, rounded=True, lw=2.5)
    ax.text(
        6.0,
        5.7,
        "Twoja aplikacja Java (JVM)",
        fontsize=FS_LABEL,
        ha="center",
        fontweight="bold",
    )

    # Kafka Consumer
    draw_box(
        ax,
        1.0,
        3.0,
        2.5,
        1.5,
        "Kafka\nConsumer\n(input topic)",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )

    # Processing
    draw_box(
        ax,
        4.5,
        3.0,
        2.5,
        1.5,
        "Kafka Streams\n(logika\nbiznesowa)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # Kafka Producer
    draw_box(
        ax,
        8.0,
        3.0,
        2.5,
        1.5,
        "Kafka\nProducer\n(output topic)",
        fill=GRAY1,
        fontsize=FS,
        fontweight="bold",
    )

    # Arrows
    draw_arrow(ax, 3.5, 3.75, 4.5, 3.75, lw=2)
    draw_arrow(ax, 7.0, 3.75, 8.0, 3.75, lw=2)

    # RocksDB state store
    draw_box(
        ax,
        4.5,
        1.0,
        2.5,
        1.3,
        "RocksDB\n(stan lokalny)",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    ax.plot([5.75, 5.75], [3.0, 2.3], color=LN, lw=1.5)
    ax.text(
        7.3,
        1.6,
        "okna, joiny,\nagregacje",
        fontsize=FS_SMALL,
        style="italic",
        va="center",
    )

    # Key message
    ax.text(
        6.0,
        0.2,
        "NIE potrzebujesz osobnego klastra!  Skalujesz = więcej instancji JVM.",
        fontsize=FS,
        ha="center",
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": LN},
    )

    save_fig(fig, "q20_kafka_streams_arch.png")


# ============================================================
# 11. Flink architecture + checkpointing
# ============================================================
def gen_flink_arch() -> None:
    """Gen flink arch."""
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_title(
        "Apache Flink — architektura klastra + checkpointing",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Cluster border
    draw_box(ax, 0.3, 1.0, 11.4, 6.2, "", fill=GRAY4, rounded=True, lw=2.5)
    ax.text(
        6.0, 6.95, "FLINK CLUSTER", fontsize=FS_LABEL, ha="center", fontweight="bold"
    )

    # Job Manager
    draw_box(
        ax,
        1.0,
        5.5,
        3.0,
        1.2,
        "Job Manager\n(koordynacja,\ncheckpointy)",
        fill=GRAY2,
        fontsize=FS,
        fontweight="bold",
    )

    # Task Managers
    draw_box(ax, 1.0, 3.0, 10.0, 2.0, "", fill="white", rounded=True, lw=1.5)
    ax.text(
        6.0, 4.7, "Task Managers (workery)", fontsize=FS, ha="center", fontweight="bold"
    )

    slots = ["source\n& map()", "map()", "window()\n& reduce", "sink()"]
    for i, s in enumerate(slots):
        x = 1.5 + i * 2.4
        draw_box(
            ax,
            x,
            3.3,
            2.0,
            1.2,
            f"Slot {i + 1}\n{s}",
            fill=GRAY1,
            fontsize=FS_SMALL,
            fontweight="bold",
        )

    draw_arrow(ax, 2.5, 5.5, 6.0, 5.0, lw=1.5, style="->")
    ax.text(5.0, 5.5, "przydziela\npodzadania", fontsize=FS_SMALL, style="italic")

    # Checkpoint storage
    draw_box(
        ax,
        5.5,
        1.2,
        3.5,
        1.2,
        "Checkpoint Storage\n(HDFS / S3)",
        fill=GRAY3,
        fontsize=FS,
        fontweight="bold",
    )
    ax.plot([7.25, 7.25], [2.4, 3.3], color=LN, lw=1.5, linestyle="--")
    ax.text(8.0, 2.7, "snapshoty\nstanu", fontsize=FS_SMALL, style="italic")

    # Barrier concept at bottom
    ax.text(3.0, 1.6, "Barrier:", fontsize=FS, fontweight="bold")
    barrier_boxes = ["source", "|B|", "map", "|B|", "sink"]
    bx = 0.8
    for _i, b in enumerate(barrier_boxes):
        if b == "|B|":
            ax.text(
                bx + 0.3,
                1.5,
                b,
                fontsize=FS,
                ha="center",
                fontweight="bold",
                bbox={"boxstyle": "round,pad=0.1", "facecolor": GRAY5, "edgecolor": LN},
            )
            draw_arrow(ax, bx, 1.5, bx + 0.1, 1.5, lw=1)
            bx += 0.7
        else:
            draw_box(
                ax,
                bx,
                1.3,
                1.0,
                0.45,
                b,
                fill=GRAY1,
                fontsize=FS_SMALL,
                fontweight="bold",
            )
            bx += 1.2

    save_fig(fig, "q20_flink_arch.png")

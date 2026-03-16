"""Johnson's algorithm Gantt chart diagram (F2||Cmax)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._sched_common import (
    BG,
    DPI,
    FONTWEIGHT_THRESHOLD,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    MIN_COLUMN_INDEX,
    OUTPUT_DIR,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)


def draw_johnson_gantt() -> None:
    """Draw johnson gantt."""
    _fig, axes = plt.subplots(
        2, 1, figsize=(8.27, 7), gridspec_kw={"height_ratios": [1, 1.8]}
    )

    _draw_johnson_decision_table(axes[0])
    _draw_johnson_gantt_chart(axes[1])

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "scheduling_johnson_gantt.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ scheduling_johnson_gantt.png")


def _draw_johnson_decision_table(ax: Axes) -> None:
    """Draw the Johnson algorithm decision table."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Algorytm Johnsona (F2 || Cmax) — Decyzja + Diagram Gantta",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Task table
    tasks = ["J1", "J2", "J3", "J4", "J5"]
    a_times = [4, 2, 6, 1, 3]
    b_times = [5, 3, 2, 7, 4]
    min_vals = [min(a, b) for a, b in zip(a_times, b_times, strict=False)]
    min_on = ["M1" if a <= b else "M2" for a, b in zip(a_times, b_times, strict=False)]
    assign = ["POCZątek" if m == "M1" else "KONIEC" for m in min_on]

    # Draw table
    col_w_t = 1.3
    row_h = 0.55
    headers = ["Zadanie", "aⱼ (M1)", "bⱼ (M2)", "min", "min na", "Przydziel"]
    table_x = 0.8
    table_y = 3.8

    for j, hdr in enumerate(headers):
        x = table_x + j * col_w_t
        rect = mpatches.Rectangle(
            (x, table_y), col_w_t, row_h, lw=1, edgecolor=LN, facecolor=GRAY2
        )
        ax.add_patch(rect)
        ax.text(
            x + col_w_t / 2,
            table_y + row_h / 2,
            hdr,
            ha="center",
            va="center",
            fontsize=6.5,
            fontweight="bold",
        )

    for i in range(5):
        row_data = [
            tasks[i],
            str(a_times[i]),
            str(b_times[i]),
            str(min_vals[i]),
            min_on[i],
            assign[i],
        ]
        for j, val in enumerate(row_data):
            x = table_x + j * col_w_t
            y = table_y - (i + 1) * row_h
            fill_c = GRAY1 if min_on[i] == "M1" else GRAY4
            if j == MIN_COLUMN_INDEX:  # min column - highlight
                fill_c = GRAY3
            rect = mpatches.Rectangle(
                (x, y), col_w_t, row_h, lw=0.8, edgecolor=LN, facecolor=fill_c
            )
            ax.add_patch(rect)
            fw = "bold" if j >= FONTWEIGHT_THRESHOLD else "normal"
            ax.text(
                x + col_w_t / 2,
                y + row_h / 2,
                val,
                ha="center",
                va="center",
                fontsize=6.5,
                fontweight=fw,
            )

    # Sorting result
    result_y = 0.7
    ax.text(
        5.0,
        result_y + 0.4,
        "Sortuj → POCZĄTEK ↑aⱼ: J4(1), J2(2), J5(3), J1(4)  |  KONIEC ↓bⱼ: J3(2)",
        ha="center",
        fontsize=7,
        color="#333333",
    )
    ax.text(
        5.0,
        result_y,
        "Optymalna kolejność:   J4 → J2 → J5 → J1 → J3",
        ha="center",
        fontsize=9,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.2",
            "facecolor": GRAY1,
            "edgecolor": LN,
            "lw": 1.2,
        },
    )


def _draw_johnson_gantt_chart(ax2: Axes) -> None:
    """Draw the Johnson algorithm Gantt chart."""
    ax2.set_xlim(-1, 24)
    ax2.set_ylim(-1, 4)
    ax2.axis("off")

    # Machines labels
    m1_y = 2.5
    m2_y = 0.8
    bar_h = 0.9

    ax2.text(
        -0.8,
        m1_y + bar_h / 2,
        "M1",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )
    ax2.text(
        -0.8,
        m2_y + bar_h / 2,
        "M2",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )

    # Schedule: J4 → J2 → J5 → J1 → J3
    order = ["J4", "J2", "J5", "J1", "J3"]
    a_ord = [1, 2, 3, 4, 6]  # M1 times in order
    b_ord = [7, 3, 4, 5, 2]  # M2 times in order
    fills = [GRAY1, GRAY2, GRAY4, GRAY3, GRAY5]
    hatches = ["", "///", "", "\\\\\\", "xxx"]

    # M1 schedule
    m1_starts = []
    t = 0
    for a in a_ord:
        m1_starts.append(t)
        t += a
    m1_ends = [s + a for s, a in zip(m1_starts, a_ord, strict=False)]

    # M2 schedule (must wait for M1 finish AND previous M2 finish)
    m2_starts = []
    m2_ends = []
    prev_m2_end = 0
    for i, b in enumerate(b_ord):
        start = max(m1_ends[i], prev_m2_end)
        m2_starts.append(start)
        m2_ends.append(start + b)
        prev_m2_end = start + b

    # Draw M1 bars
    for i in range(5):
        rect = mpatches.Rectangle(
            (m1_starts[i], m1_y),
            a_ord[i],
            bar_h,
            lw=1.2,
            edgecolor=LN,
            facecolor=fills[i],
            hatch=hatches[i],
        )
        ax2.add_patch(rect)
        ax2.text(
            m1_starts[i] + a_ord[i] / 2,
            m1_y + bar_h / 2,
            f"{order[i]}\n({a_ord[i]})",
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
        )

    # Draw M2 bars
    for i in range(5):
        rect = mpatches.Rectangle(
            (m2_starts[i], m2_y),
            b_ord[i],
            bar_h,
            lw=1.2,
            edgecolor=LN,
            facecolor=fills[i],
            hatch=hatches[i],
        )
        ax2.add_patch(rect)
        ax2.text(
            m2_starts[i] + b_ord[i] / 2,
            m2_y + bar_h / 2,
            f"{order[i]}\n({b_ord[i]})",
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
        )

    # Draw idle regions on M2
    idle_starts = [0]
    idle_ends = [m2_starts[0]]
    for i in range(1, 5):
        if m2_starts[i] > m2_ends[i - 1]:
            idle_starts.append(m2_ends[i - 1])
            idle_ends.append(m2_starts[i])

    for s, e in zip(idle_starts, idle_ends, strict=False):
        if e > s:
            rect = mpatches.Rectangle(
                (s, m2_y),
                e - s,
                bar_h,
                lw=0.5,
                edgecolor="#AAAAAA",
                facecolor="white",
                linestyle="--",
            )
            ax2.add_patch(rect)
            ax2.text(
                s + (e - s) / 2,
                m2_y + bar_h / 2,
                "idle",
                ha="center",
                va="center",
                fontsize=5,
                color="#999999",
            )

    # Time axis
    ax_y = m2_y - 0.15
    ax2.plot([0, 23], [ax_y, ax_y], color=LN, lw=0.8)
    for t in range(0, 24, 2):
        ax2.plot([t, t], [ax_y - 0.08, ax_y + 0.08], color=LN, lw=0.8)
        ax2.text(t, ax_y - 0.25, str(t), ha="center", va="top", fontsize=6)
    ax2.text(11.5, ax_y - 0.55, "czas", ha="center", fontsize=7)

    # Cmax annotation
    ax2.annotate(
        f"Cmax = {m2_ends[-1]}",
        xy=(m2_ends[-1], m2_y + bar_h),
        xytext=(m2_ends[-1] + 0.5, m2_y + bar_h + 0.6),
        fontsize=10,
        fontweight="bold",
        color="#333333",
        arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 1.5},
    )

    # Mnemonic at bottom
    ax2.text(
        11,
        -0.7,
        "„Krótki na M1 → START (szybko karmi M2)"
        "      Krótki na M2 → KONIEC"
        ' (szybko kończy)"',
        ha="center",
        fontsize=7.5,
        fontweight="bold",
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
            "lw": 0.8,
        },
    )

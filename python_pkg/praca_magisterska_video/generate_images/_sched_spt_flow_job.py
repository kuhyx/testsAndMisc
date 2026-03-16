"""SPT vs LPT comparison and Flow Shop vs Job Shop diagrams."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._sched_common import (
    BG,
    DPI,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    OUTPUT_DIR,
    draw_arrow,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)


# ============================================================
# SPT vs LPT COMPARISON (1 || ΣCⱼ)
# ============================================================
def draw_spt_comparison() -> None:
    """Draw spt comparison."""
    fig, axes = plt.subplots(2, 1, figsize=(8.27, 5.5))

    tasks_orig = [("J1", 5), ("J2", 3), ("J3", 8), ("J4", 2), ("J5", 6)]

    spt_order = sorted(tasks_orig, key=lambda x: x[1])
    lpt_order = sorted(tasks_orig, key=lambda x: -x[1])

    fills_map = {"J1": GRAY1, "J2": GRAY2, "J3": GRAY3, "J4": GRAY4, "J5": GRAY5}
    hatch_map = {"J1": "", "J2": "///", "J3": "xxx", "J4": "", "J5": "\\\\\\"}

    for _idx, (ax, order_list, title, is_optimal) in enumerate(
        [
            (axes[0], spt_order, "SPT (Shortest Processing Time) — OPTYMALNE", True),
            (axes[1], lpt_order, "LPT (Longest Processing Time) — gorsze!", False),
        ]
    ):
        ax.set_xlim(-2, 26)
        ax.set_ylim(-0.5, 2.5)
        ax.axis("off")
        color = "#222222" if is_optimal else "#666666"
        marker = "✓" if is_optimal else "✗"
        ax.set_title(
            f"{marker} {title}",
            fontsize=9,
            fontweight="bold",
            loc="left",
            color=color,
            pad=5,
        )

        bar_y = 1.0
        bar_h = 0.8
        t = 0
        completions = []

        for name, duration in order_list:
            rect = mpatches.Rectangle(
                (t, bar_y),
                duration,
                bar_h,
                lw=1.2,
                edgecolor=LN,
                facecolor=fills_map[name],
                hatch=hatch_map[name],
            )
            ax.add_patch(rect)
            ax.text(
                t + duration / 2,
                bar_y + bar_h / 2,
                f"{name}\n({duration})",
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold",
            )
            t += duration
            completions.append(t)

            # Completion time marker
            ax.plot([t, t], [bar_y - 0.15, bar_y], color=LN, lw=0.8)
            ax.text(
                t,
                bar_y - 0.25,
                f"C={t}",
                ha="center",
                va="top",
                fontsize=6,
                color="#555555",
            )

        total = sum(completions)
        # Time axis
        ax.plot([0, 25], [bar_y - 0.05, bar_y - 0.05], color=LN, lw=0.5)

        # Sum annotation
        comp_str = " + ".join(str(c) for c in completions)
        ax.text(
            25,
            bar_y + bar_h / 2,
            f"ΣCⱼ = {comp_str}\n    = {total}",
            ha="left",
            va="center",
            fontsize=7,
            fontweight="bold" if is_optimal else "normal",
            color=color,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": GRAY1 if is_optimal else "white",
                "edgecolor": color,
                "lw": 1,
            },
        )

    # Bottom annotation
    fig.text(
        0.5,
        0.02,
        '„Short People To the front"'
        " — krótkie najpierw,"
        " jak niskie osoby w zdjęciu klasowym",
        ha="center",
        fontsize=8,
        fontweight="bold",
        style="italic",
        color="#444444",
    )

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(
        str(Path(OUTPUT_DIR) / "scheduling_spt_comparison.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ scheduling_spt_comparison.png")


# ============================================================
# FLOW SHOP vs JOB SHOP
# ============================================================
def draw_flow_vs_job() -> None:
    """Draw flow vs job."""
    _fig, axes = plt.subplots(1, 2, figsize=(8.27, 4.5))

    _draw_flow_shop(axes[0])
    _draw_job_shop(axes[1])

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "scheduling_flow_vs_job.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ scheduling_flow_vs_job.png")


def _draw_flow_shop(ax: Axes) -> None:
    """Draw the Flow Shop diagram."""
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Flow Shop (Fm)", fontsize=10, fontweight="bold", pad=8)

    # Machines in a row
    machines_x = [1, 3, 5]
    machines_y = 3
    mach_r = 0.4

    for i, mx in enumerate(machines_x):
        circle = plt.Circle(
            (mx, machines_y), mach_r, facecolor=GRAY2, edgecolor=LN, lw=1.5
        )
        ax.add_patch(circle)
        ax.text(
            mx,
            machines_y,
            f"M{i + 1}",
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    # Arrows between machines
    for i in range(len(machines_x) - 1):
        draw_arrow(
            ax,
            machines_x[i] + mach_r + 0.05,
            machines_y,
            machines_x[i + 1] - mach_r - 0.05,
            machines_y,
            lw=2,
        )

    # Jobs all flowing the same way
    jobs_flow = ["J1", "J2", "J3"]
    for _j, (job, y_off) in enumerate(zip(jobs_flow, [0.8, 0, -0.8], strict=False)):
        ax.text(
            0.2,
            machines_y + y_off,
            job,
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": GRAY1, "edgecolor": LN},
        )
        # Dashed flow line
        ax.annotate(
            "",
            xy=(5.5, machines_y + y_off * 0.3),
            xytext=(0.5, machines_y + y_off),
            arrowprops={
                "arrowstyle": "->",
                "color": "#888888",
                "lw": 0.8,
                "linestyle": "dashed",
            },
        )

    ax.text(
        3,
        1.2,
        "Wszystkie zadania:\nM1 → M2 → M3",
        ha="center",
        va="center",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    ax.text(
        3,
        0.4,
        "Jak taśma montażowa",
        ha="center",
        fontsize=7,
        style="italic",
        color="#666666",
    )


def _draw_job_shop(ax: Axes) -> None:
    """Draw the Job Shop diagram."""
    mach_r = 0.4
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Job Shop (Jm)", fontsize=10, fontweight="bold", pad=8)

    # Machines scattered
    m_positions = [(1.5, 4.2), (4.5, 4.2), (3, 2.5)]

    for i, (mx, my) in enumerate(m_positions):
        circle = plt.Circle((mx, my), mach_r, facecolor=GRAY2, edgecolor=LN, lw=1.5)
        ax.add_patch(circle)
        ax.text(
            mx, my, f"M{i + 1}", ha="center", va="center", fontsize=9, fontweight="bold"
        )

    # J1: M1 → M2 → M3 (solid)
    route1 = [(1.5, 4.2), (4.5, 4.2), (3, 2.5)]
    for i in range(len(route1) - 1):
        x1, y1 = route1[i]
        x2, y2 = route1[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        d = (dx**2 + dy**2) ** 0.5
        draw_arrow(
            ax,
            x1 + mach_r * dx / d + 0.05,
            y1 + mach_r * dy / d,
            x2 - mach_r * dx / d - 0.05,
            y2 - mach_r * dy / d,
            lw=1.5,
        )
    ax.text(
        0.3,
        4.8,
        "J1: M1→M2→M3",
        fontsize=7,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.1", "facecolor": GRAY1, "edgecolor": LN},
    )

    # J2: M2 → M3 → M1 (dashed)
    route2 = [(4.5, 4.2), (3, 2.5), (1.5, 4.2)]
    for i in range(len(route2) - 1):
        x1, y1 = route2[i]
        x2, y2 = route2[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        d = (dx**2 + dy**2) ** 0.5
        off = 0.15  # offset to avoid overlap
        ax.annotate(
            "",
            xy=(x2 - mach_r * dx / d - 0.05, y2 - mach_r * dy / d + off),
            xytext=(x1 + mach_r * dx / d + 0.05, y1 + mach_r * dy / d + off),
            arrowprops={
                "arrowstyle": "->",
                "color": "#555555",
                "lw": 1.5,
                "linestyle": "dashed",
            },
        )
    ax.text(
        3.8,
        5.2,
        "J2: M2→M3→M1",
        fontsize=7,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.1", "facecolor": GRAY4, "edgecolor": LN},
    )

    ax.text(
        3,
        1.2,
        "Każde zadanie:\nwłasna trasa!",
        ha="center",
        va="center",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    ax.text(
        3,
        0.4,
        "NP-trudny już dla 3 maszyn",
        ha="center",
        fontsize=7,
        style="italic",
        color="#666666",
    )

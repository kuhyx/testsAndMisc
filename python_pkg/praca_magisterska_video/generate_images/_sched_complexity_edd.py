"""Scheduling complexity landscape and EDD example diagrams."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._sched_common import (
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    OUTPUT_DIR,
    draw_arrow,
)

_logger = logging.getLogger(__name__)


# ============================================================
# SCHEDULING COMPLEXITY LANDSCAPE
# ============================================================
def draw_complexity_map() -> None:
    """Draw complexity map."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Złożoność problemów szeregowania — od łatwych do NP-trudnych",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Gradient arrow at the top
    ax.annotate(
        "",
        xy=(9.5, 6.2),
        xytext=(0.5, 6.2),
        arrowprops={"arrowstyle": "->", "color": LN, "lw": 2},
    )
    ax.text(5, 6.5, "Rosnąca złożoność", ha="center", fontsize=9, fontweight="bold")

    # Easy (polynomial) region
    easy_rect = FancyBboxPatch(
        (0.3, 2.8),
        4.0,
        3.0,
        boxstyle="round,pad=0.15",
        lw=1.5,
        edgecolor="#666666",
        facecolor=GRAY4,
        linestyle="-",
    )
    ax.add_patch(easy_rect)
    ax.text(
        2.3,
        5.5,
        "WIELOMIANOWE  O(n log n)",
        ha="center",
        fontsize=9,
        fontweight="bold",
        color="#444444",
    )

    easy_problems = [
        ("1 || ΣCⱼ", "SPT", GRAY1, 4.8),
        ("1 || Lmax", "EDD", GRAY2, 4.0),
        ("F2 || Cmax", "Johnson", GRAY1, 3.2),
    ]
    for prob, method, fill, y in easy_problems:
        rect = FancyBboxPatch(
            (0.6, y),
            3.5,
            0.6,
            boxstyle="round,pad=0.05",
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            1.2,
            y + 0.3,
            prob,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            fontfamily="monospace",
        )
        ax.text(3.0, y + 0.3, f"→ {method}", ha="center", va="center", fontsize=8)

    # Hard (NP) region
    hard_rect = FancyBboxPatch(
        (5.3, 2.8),
        4.3,
        3.0,
        boxstyle="round,pad=0.15",
        lw=1.5,
        edgecolor="#444444",
        facecolor=GRAY3,
        linestyle="-",
    )
    ax.add_patch(hard_rect)
    ax.text(
        7.45,
        5.5,
        "NP-TRUDNE",
        ha="center",
        fontsize=9,
        fontweight="bold",
        color="#333333",
    )

    hard_problems = [
        ("Pm || Cmax\n(m≥2)", "LPT heuryst.", GRAY2, 4.5),
        ("1 || ΣTⱼ", "branch&bound", GRAY4, 3.7),
        ("Jm || Cmax\n(m≥3)", "metaheuryst.", GRAY5, 2.9),
    ]
    for prob, method, fill, y in hard_problems:
        rect = FancyBboxPatch(
            (5.6, y),
            3.7,
            0.7,
            boxstyle="round,pad=0.05",
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            6.5,
            y + 0.35,
            prob,
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
            fontfamily="monospace",
        )
        ax.text(8.2, y + 0.35, f"→ {method}", ha="center", va="center", fontsize=7)

    # Arrow connecting
    draw_arrow(ax, 4.4, 4.0, 5.2, 4.0, lw=2, color="#888888")
    ax.text(4.8, 4.25, "+1\nmaszyna", ha="center", fontsize=6, color="#888888")

    # Bottom: key insight
    ax.text(
        5.0,
        1.8,
        "„Dodanie jednej maszyny lub jednego ograniczenia\n"
        'może zmienić problem z łatwego na NP-trudny!"',
        ha="center",
        fontsize=8,
        fontweight="bold",
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
            "lw": 1,
        },
    )

    # Bottom examples
    ax.text(
        5.0,
        0.8,
        "1 maszyna → łatwe (sortuj)  |  ≥2 maszyny równoległe → NP-trudne\n"
        "Flow shop 2 maszyny → Johnson O(n log n)  |  Flow shop 3 maszyny → NP-trudne",
        ha="center",
        fontsize=7,
        color="#555555",
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "scheduling_complexity_map.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ scheduling_complexity_map.png")


# ============================================================
# EDD EXAMPLE (1 || Lmax)
# ============================================================
def draw_edd_example() -> None:
    """Draw edd example."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 4))
    ax.set_xlim(-2, 28)
    ax.set_ylim(-2, 4)
    ax.axis("off")
    ax.set_title(
        "EDD (Earliest Due Date) — 1 || Lmax  — Przykład",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=8,
    )

    # Tasks: name, processing time, due date
    tasks = [("J1", 4, 10), ("J2", 2, 6), ("J3", 6, 15), ("J4", 3, 8), ("J5", 5, 18)]
    # EDD: sort by due date
    edd_order = sorted(tasks, key=lambda x: x[2])

    bar_y = 1.5
    bar_h = 0.8
    t = 0
    fills_edd = [GRAY1, GRAY2, GRAY4, GRAY3, GRAY5]

    lateness_vals = []
    for i, (name, p, d) in enumerate(edd_order):
        rect = mpatches.Rectangle(
            (t, bar_y), p, bar_h, lw=1.2, edgecolor=LN, facecolor=fills_edd[i]
        )
        ax.add_patch(rect)
        ax.text(
            t + p / 2,
            bar_y + bar_h / 2,
            f"{name}\np={p}, d={d}",
            ha="center",
            va="center",
            fontsize=6.5,
            fontweight="bold",
        )
        t += p
        lateness = t - d
        lateness_vals.append(lateness)

        # Due date marker
        ax.plot(
            [d, d], [bar_y - 0.4, bar_y - 0.1], color="#888888", lw=0.8, linestyle="--"
        )
        ax.text(
            d,
            bar_y - 0.5,
            f"d={d}",
            ha="center",
            va="top",
            fontsize=5.5,
            color="#888888",
        )

        # Completion + lateness
        ax.plot([t, t], [bar_y + bar_h, bar_y + bar_h + 0.15], color=LN, lw=0.8)
        ax.text(
            t,
            bar_y + bar_h + 0.2,
            f"C={t}\nL={lateness}",
            ha="center",
            va="bottom",
            fontsize=5.5,
        )

    # Time axis
    ax.plot([0, 22], [bar_y - 0.05, bar_y - 0.05], color=LN, lw=0.5)

    lmax = max(lateness_vals)
    ax.text(
        22,
        bar_y + bar_h / 2,
        f"Lmax = {lmax}",
        ha="left",
        va="center",
        fontsize=10,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY1, "edgecolor": LN},
    )

    # Bottom mnemonic
    ax.text(
        10,
        -1.3,
        '„Early Due Date Does it first" — najpilniejszy deadline idzie pierwszy',
        ha="center",
        fontsize=8,
        fontweight="bold",
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
            "lw": 0.8,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "scheduling_edd_example.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ scheduling_edd_example.png")

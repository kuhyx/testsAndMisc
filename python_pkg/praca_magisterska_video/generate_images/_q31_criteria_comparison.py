"""Q31 Diagram 1: Payoff matrix + all criteria bar chart."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from python_pkg.praca_magisterska_video.generate_images._q31_common import (
    _DATA_STATE_COLS,
    BG,
    DPI,
    FS,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    OUTPUT_DIR,
    _logger,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _draw_payoff_table(ax: Axes) -> None:
    """Draw the payoff matrix table on the left panel."""
    ax.axis("off")
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 6)
    ax.set_title(
        "Macierz wypłat (tys. zł)",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=8,
    )

    headers_col = ["", "S₁\n(dobra)", "S₂\n(średnia)", "S₃\n(zła)"]
    rows = [
        ["A₁ (fabryka)", "200", "50", "-100"],
        ["A₂ (sklep)", "80", "70", "40"],
        ["A₃ (obligacje)", "30", "30", "30"],
    ]

    col_w = [1.8, 1.2, 1.2, 1.2]
    row_h = 0.7
    start_y = 4.5
    start_x = 0.2

    # Draw header row
    x = start_x
    for j, h in enumerate(headers_col):
        fill = GRAY2 if j > 0 else GRAY3
        rect = mpatches.Rectangle(
            (x, start_y),
            col_w[j],
            row_h,
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            x + col_w[j] / 2,
            start_y + row_h / 2,
            h,
            ha="center",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )
        x += col_w[j]

    # Draw data rows
    for i, row in enumerate(rows):
        x = start_x
        y = start_y - (i + 1) * row_h
        for j, val in enumerate(row):
            fill = GRAY4 if j == 0 else ("white" if i % 2 == 0 else GRAY1)
            if val.startswith("-"):
                fill = "#D8D8D8"
            rect = mpatches.Rectangle(
                (x, y),
                col_w[j],
                row_h,
                lw=1,
                edgecolor=LN,
                facecolor=fill,
            )
            ax.add_patch(rect)
            fw = "bold" if j == 0 else "normal"
            ax.text(
                x + col_w[j] / 2,
                y + row_h / 2,
                val,
                ha="center",
                va="center",
                fontsize=FS,
                fontweight=fw,
            )
            x += col_w[j]

    # Probability row for EV
    x = start_x
    y = start_y - 4 * row_h
    probs = ["p (dla E[X]):", "0.5", "0.3", "0.2"]
    for j, val in enumerate(probs):
        fill = GRAY5 if j > 0 else GRAY3
        rect = mpatches.Rectangle(
            (x, y),
            col_w[j],
            row_h * 0.7,
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            x + col_w[j] / 2,
            y + row_h * 0.35,
            val,
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
            style="italic",
        )
        x += col_w[j]


def _draw_criteria_bars(ax2: Axes) -> None:
    """Draw the criteria comparison bar chart on the right panel."""
    criteria = [
        "E[X]",
        "Laplace",
        "Maximax",
        "Maximin",
        "Hurwicz\n\u03b1=0.6",
        "Savage",
    ]

    ev = [95, 69, 30]
    laplace = [50, 63.3, 30]
    maximax = [200, 80, 30]
    maximin = [-100, 40, 30]
    hurwicz = [80, 64, 30]
    savage_maxregret = [140, 120, 170]

    winners = [0, 1, 0, 1, 0, 1]

    x_pos = np.arange(len(criteria))
    width = 0.22
    hatches = ["///", "...", "xxx"]
    labels = ["A₁ (fabryka)", "A₂ (sklep)", "A₃ (obligacje)"]

    all_vals = [
        [
            ev[0],
            laplace[0],
            maximax[0],
            maximin[0],
            hurwicz[0],
            savage_maxregret[0],
        ],
        [
            ev[1],
            laplace[1],
            maximax[1],
            maximin[1],
            hurwicz[1],
            savage_maxregret[1],
        ],
        [
            ev[2],
            laplace[2],
            maximax[2],
            maximin[2],
            hurwicz[2],
            savage_maxregret[2],
        ],
    ]

    for i in range(_DATA_STATE_COLS):
        ax2.bar(
            x_pos + (i - 1) * width,
            all_vals[i],
            width,
            label=labels[i],
            color="white",
            edgecolor=LN,
            hatch=hatches[i],
            lw=0.8,
        )

    for c_idx in range(len(criteria)):
        w = winners[c_idx]
        val = all_vals[w][c_idx]
        ax2.text(
            x_pos[c_idx] + (w - 1) * width,
            val + 5,
            "★",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(criteria, fontsize=7)
    ax2.set_ylabel("Wartość kryterium", fontsize=8)
    ax2.set_title(
        "Porównanie kryteriów",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=8,
    )
    ax2.legend(fontsize=7, loc="upper right")
    ax2.axhline(y=0, color=LN, lw=0.5, ls="-")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.tick_params(labelsize=7)

    ax2.text(
        5,
        -30,
        "(Savage: niżej\n= lepiej)",
        fontsize=6,
        ha="center",
        va="top",
        style="italic",
    )


def draw_criteria_comparison() -> None:
    """Draw payoff matrix and criteria comparison chart."""
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(8.27, 4.5),
        gridspec_kw={"width_ratios": [1.2, 1]},
    )

    _draw_payoff_table(axes[0])
    _draw_criteria_bars(axes[1])

    plt.tight_layout()
    outpath = str(Path(OUTPUT_DIR) / "q31_criteria_comparison.png")
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", outpath)

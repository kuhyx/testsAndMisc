"""Q31 Diagram 2: Regret matrix construction step-by-step."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._q31_common import (
    _DATA_STATE_COLS,
    _REGRET_HEADER_COLS,
    BG,
    DPI,
    FS,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    LN,
    OUTPUT_DIR,
    _logger,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _draw_original_payoff(
    ax: Axes,
    start_y: float,
    row_h: float,
) -> None:
    """Draw the original payoff matrix (left side of regret fig)."""
    ax.text(
        2.2,
        6.3,
        "Krok 1: Macierz wypłat",
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="center",
    )

    col_w = 1.0
    headers = ["", "S₁", "S₂", "S₃"]
    data = [
        ["A₁", "200", "50", "-100"],
        ["A₂", "80", "70", "40"],
        ["A₃", "30", "30", "30"],
    ]
    start_x = 0.3

    for j, h in enumerate(headers):
        w = 0.7 if j == 0 else col_w
        x = start_x + (0 if j == 0 else 0.7 + (j - 1) * col_w)
        rect = mpatches.Rectangle(
            (x, start_y),
            w,
            row_h,
            lw=1,
            edgecolor=LN,
            facecolor=GRAY2,
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2,
            start_y + row_h / 2,
            h,
            ha="center",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )

    for i, row in enumerate(data):
        y = start_y - (i + 1) * row_h
        for j, val in enumerate(row):
            w = 0.7 if j == 0 else col_w
            x = start_x + (0 if j == 0 else 0.7 + (j - 1) * col_w)
            fill = GRAY4 if j == 0 else "white"
            rect = mpatches.Rectangle(
                (x, y),
                w,
                row_h,
                lw=1,
                edgecolor=LN,
                facecolor=fill,
            )
            ax.add_patch(rect)
            ax.text(
                x + w / 2,
                y + row_h / 2,
                val,
                ha="center",
                va="center",
                fontsize=FS,
            )

    # Max per column annotation
    max_y = start_y - _DATA_STATE_COLS * row_h - 0.1
    col_maxes = ["max=200", "max=70", "max=40"]
    for idx, label in enumerate(col_maxes):
        ax.text(
            start_x + 0.7 + (idx + 0.5) * col_w,
            max_y,
            label,
            fontsize=7,
            ha="center",
            va="top",
            fontweight="bold",
            color="#333",
        )

    # Arrow
    ax.annotate(
        "",
        xy=(5.0, 4.8),
        xytext=(4.2, 4.8),
        arrowprops={"arrowstyle": "->", "color": LN, "lw": 2},
    )
    ax.text(
        4.6,
        5.0,
        "rᵢⱼ = max - aᵢⱼ",
        fontsize=8,
        ha="center",
        va="bottom",
        fontweight="bold",
    )


def _draw_regret_table(
    ax: Axes,
    start_y: float,
    row_h: float,
) -> None:
    """Draw the regret matrix (right side of regret fig)."""
    ax.text(
        7.5,
        6.3,
        "Krok 2: Macierz żalu",
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="center",
    )

    regret_data = [
        ["A₁", "0", "20", "140"],
        ["A₂", "120", "0", "0"],
        ["A₃", "170", "40", "10"],
    ]
    headers2 = ["", "S₁", "S₂", "S₃", "max rᵢ"]
    start_x2 = 5.3

    for j, h in enumerate(headers2):
        w = 0.7 if j == 0 else (0.9 if j < _REGRET_HEADER_COLS else 1.0)
        x = start_x2
        if j == 0:
            x = start_x2
        elif j <= _DATA_STATE_COLS:
            x = start_x2 + 0.7 + (j - 1) * 0.9
        else:
            x = start_x2 + 0.7 + _DATA_STATE_COLS * 0.9
        rect = mpatches.Rectangle(
            (x, start_y),
            w,
            row_h,
            lw=1,
            edgecolor=LN,
            facecolor=(GRAY2 if j < _REGRET_HEADER_COLS else GRAY3),
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2,
            start_y + row_h / 2,
            h,
            ha="center",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )

    max_regrets = [140, 120, 170]
    for i, row in enumerate(regret_data):
        y = start_y - (i + 1) * row_h
        for j, val in enumerate(row):
            w = 0.7 if j == 0 else 0.9
            x = start_x2 + (0 if j == 0 else 0.7 + (j - 1) * 0.9)
            fill = GRAY4 if j == 0 else "white"
            if j > 0 and int(val) == max_regrets[i]:
                fill = GRAY2
            rect = mpatches.Rectangle(
                (x, y),
                w,
                row_h,
                lw=1,
                edgecolor=LN,
                facecolor=fill,
            )
            ax.add_patch(rect)
            fw = "bold" if (j > 0 and int(val) == max_regrets[i]) else "normal"
            ax.text(
                x + w / 2,
                y + row_h / 2,
                val,
                ha="center",
                va="center",
                fontsize=FS,
                fontweight=fw,
            )

        # Max regret column
        x = start_x2 + 0.7 + _DATA_STATE_COLS * 0.9
        w = 1.0
        is_winner = max_regrets[i] == min(max_regrets)
        fill = "#C8C8C8" if is_winner else GRAY1
        rect = mpatches.Rectangle(
            (x, y),
            w,
            row_h,
            lw=1.5 if is_winner else 1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        marker = " ★" if is_winner else ""
        ax.text(
            x + w / 2,
            y + row_h / 2,
            f"{max_regrets[i]}{marker}",
            ha="center",
            va="center",
            fontsize=FS,
            fontweight="bold",
        )


def draw_regret_matrix() -> None:
    """Draw the regret matrix construction diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 5))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_title(
        "Kryterium Savage'a \u2014 budowa macierzy żalu",
        fontsize=FS_TITLE + 1,
        fontweight="bold",
        pad=10,
    )

    start_y = 5.5
    row_h = 0.55

    _draw_original_payoff(ax, start_y, row_h)
    _draw_regret_table(ax, start_y, row_h)

    # Bottom conclusion
    ax.text(
        5.0,
        2.8,
        "Krok 3: Wybierz min z max żalu" " → A₂ (max żal = 120)",
        fontsize=10,
        ha="center",
        va="center",
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY1,
            "edgecolor": LN,
            "lw": 1.5,
        },
    )

    # Interpretation examples
    ax.text(
        5.0,
        2.0,
        "Interpretacja żalu: r₁₃ = 140 oznacza:\n"
        "\u201eGdyby nastąpił S₃ (zła koniunktura),"
        " a wybrałbym A₁,\n"
        "żałowałbym, bo najlepszą opcją byłoby"
        " A₂ z wynikiem 40 \u2014 traciłbym 140\u201d",
        fontsize=7.5,
        ha="center",
        va="center",
        style="italic",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
            "lw": 0.8,
        },
    )

    # Mnemonic
    ax.text(
        5.0,
        0.8,
        "Mnemonik: Savage = \u201eŻal jak nóż\u201d\n"
        "Maksymalny żal to nóż "
        "\u2014 wybierz opcję z NAJMNIEJSZYM nożem",
        fontsize=8,
        ha="center",
        va="center",
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": "white",
            "edgecolor": LN,
            "lw": 1,
        },
    )

    plt.tight_layout()
    outpath = str(Path(OUTPUT_DIR) / "q31_regret_matrix.png")
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", outpath)

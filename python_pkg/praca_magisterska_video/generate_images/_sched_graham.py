"""Graham notation α|β|γ visual mnemonic map diagram."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

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
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)


def draw_graham_notation() -> None:
    """Draw graham notation."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Notacja Grahama  \u03b1 | β | \u03b3  — Mapa mnemoniczna",
        fontsize=FS_TITLE + 1,
        fontweight="bold",
        pad=12,
    )

    _draw_graham_formula_bar(ax)
    _draw_graham_alpha_beta(ax)
    _draw_graham_lower(ax)

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "scheduling_graham_notation.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ scheduling_graham_notation.png")


def _draw_graham_formula_bar(ax: Axes) -> None:
    """Draw the top alpha|beta|gamma formula bar."""
    bar_y = 12.5
    bar_h = 1.0
    # alpha box
    rect = FancyBboxPatch(
        (0.5, bar_y),
        2.5,
        bar_h,
        boxstyle="round,pad=0.08",
        lw=2,
        edgecolor=LN,
        facecolor=GRAY1,
    )
    ax.add_patch(rect)
    ax.text(
        1.75,
        bar_y + bar_h / 2,
        "\u03b1",
        fontsize=20,
        fontweight="bold",
        ha="center",
        va="center",
    )
    ax.text(
        1.75,
        bar_y - 0.25,
        "MASZYNY",
        fontsize=8,
        fontweight="bold",
        ha="center",
        va="top",
        color="#444444",
    )

    # separator |
    ax.text(
        3.3,
        bar_y + bar_h / 2,
        "|",
        fontsize=24,
        fontweight="bold",
        ha="center",
        va="center",
    )

    # β box
    rect = FancyBboxPatch(
        (3.7, bar_y),
        2.5,
        bar_h,
        boxstyle="round,pad=0.08",
        lw=2,
        edgecolor=LN,
        facecolor=GRAY2,
    )
    ax.add_patch(rect)
    ax.text(
        4.95,
        bar_y + bar_h / 2,
        "β",
        fontsize=20,
        fontweight="bold",
        ha="center",
        va="center",
    )
    ax.text(
        4.95,
        bar_y - 0.25,
        "OGRANICZENIA",
        fontsize=8,
        fontweight="bold",
        ha="center",
        va="top",
        color="#444444",
    )

    # separator |
    ax.text(
        6.5,
        bar_y + bar_h / 2,
        "|",
        fontsize=24,
        fontweight="bold",
        ha="center",
        va="center",
    )

    # gamma box
    rect = FancyBboxPatch(
        (6.9, bar_y),
        2.5,
        bar_h,
        boxstyle="round,pad=0.08",
        lw=2,
        edgecolor=LN,
        facecolor=GRAY3,
    )
    ax.add_patch(rect)
    ax.text(
        8.15,
        bar_y + bar_h / 2,
        "\u03b3",
        fontsize=20,
        fontweight="bold",
        ha="center",
        va="center",
    )
    ax.text(
        8.15,
        bar_y - 0.25,
        "CEL",
        fontsize=8,
        fontweight="bold",
        ha="center",
        va="top",
        color="#444444",
    )


def _draw_graham_alpha_beta(ax: Axes) -> None:
    """Draw alpha (machines) and beta (constraints) sections."""
    start_x = 0.3
    col_w = 1.28

    # === SECTION alpha: MACHINES ===
    sec_y = 11.5
    ax.text(
        0.3,
        sec_y,
        '\u03b1 — „1 Prawdziwy Quasi-Rycerz Forsuje Jaskinię Orków"',
        fontsize=8,
        fontweight="bold",
        va="top",
        style="italic",
        color="#333333",
    )

    alpha_items = [
        ("1", "jedna maszyna", "●", GRAY4),
        ("Pm", "identyczne Parallel", "●●●", GRAY1),
        ("Qm", "Quasi-uniform\n(różne prędkości)", "●●◐", GRAY4),
        ("Rm", "Random unrelated\n(czasy per para)", "●◆▲", GRAY1),
        ("Fm", "Flow shop\n(ta sama kolejność)", "→→→", GRAY2),
        ("Jm", "Job shop\n(indyw. trasy)", "↗↙↘", GRAY4),
        ("Om", "Open shop\n(dowolna kolej.)", "?→?", GRAY1),
    ]

    col_w = 1.28
    box_h_a = 1.1
    start_x = 0.3
    start_y = 9.6

    for i, (symbol, desc, icon, fill) in enumerate(alpha_items):
        x = start_x + i * col_w
        y = start_y
        rect = FancyBboxPatch(
            (x, y),
            col_w - 0.1,
            box_h_a,
            boxstyle="round,pad=0.04",
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            x + (col_w - 0.1) / 2,
            y + box_h_a - 0.15,
            symbol,
            ha="center",
            va="top",
            fontsize=9,
            fontweight="bold",
        )
        ax.text(
            x + (col_w - 0.1) / 2,
            y + box_h_a / 2 - 0.1,
            desc,
            ha="center",
            va="center",
            fontsize=5.5,
        )
        ax.text(
            x + (col_w - 0.1) / 2, y + 0.12, icon, ha="center", va="bottom", fontsize=7
        )

    # Complexity arrow under alpha
    arr_y = 9.35
    ax.annotate(
        "",
        xy=(9.0, arr_y),
        xytext=(0.5, arr_y),
        arrowprops={"arrowstyle": "->", "color": "#666666", "lw": 1.5},
    )
    ax.text(
        4.8,
        arr_y - 0.18,
        "rosnąca złożoność →",
        ha="center",
        fontsize=6,
        color="#666666",
    )

    # === SECTION β: CONSTRAINTS ===
    sec_y2 = 8.9
    ax.text(
        0.3,
        sec_y2,
        "β — „Robak Daje Deadline: Przerwy Poprzedzają Pojedyncze Setup'y\"",
        fontsize=8,
        fontweight="bold",
        va="top",
        style="italic",
        color="#333333",
    )

    beta_items = [
        ("rⱼ", "release\ndates", "Robak\ndostępne\nod czasu rⱼ", GRAY1),
        ("dⱼ", "due\ndates", "Daje\ntermin soft\n(kara za spóźn.)", GRAY4),
        ("d̄ⱼ", "dead-\nlines", "Deadline\ntermin hard\n(musi dotrzymać)", GRAY1),
        ("pmtn", "preemp-\ntion", "Przerwy\nmożna\nprzerwać", GRAY2),
        ("prec", "prece-\ndencje", "Poprzedzają\nA->B (DAG)", GRAY4),
        ("pⱼ=1", "unit\ntime", "Pojedyncze\nwszystkie = 1", GRAY1),
        ("sⱼₖ", "setup\ntimes", "Setup'y\nprzezbrojenie\nmiędzy j->k", GRAY4),
    ]

    start_y2 = 7.0
    box_h_b = 1.4

    for i, (symbol, _label, desc, fill) in enumerate(beta_items):
        x = start_x + i * col_w
        y = start_y2
        rect = FancyBboxPatch(
            (x, y),
            col_w - 0.1,
            box_h_b,
            boxstyle="round,pad=0.04",
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            x + (col_w - 0.1) / 2,
            y + box_h_b - 0.12,
            symbol,
            ha="center",
            va="top",
            fontsize=9,
            fontweight="bold",
        )
        ax.text(
            x + (col_w - 0.1) / 2,
            y + box_h_b / 2 - 0.05,
            desc,
            ha="center",
            va="center",
            fontsize=5,
        )


def _draw_graham_lower(ax: Axes) -> None:
    """Draw gamma criteria, examples, and footer sections."""
    start_x = 0.3

    # === SECTION gamma: CRITERIA ===
    sec_y3 = 6.5
    ax.text(
        0.3,
        sec_y3,
        '\u03b3 — „Ciężki Sum Ważony Lata, Tardiness Uderza"',
        fontsize=8,
        fontweight="bold",
        va="top",
        style="italic",
        color="#333333",
    )

    gamma_items = [
        ("Cmax", "makespan\nmax(Cⱼ)", "Jak długo\ntrwa WSZYSTKO?", GRAY2),
        ("ΣCⱼ", "suma\nukończeń", "Średni czas\noczekiwania?", GRAY4),
        ("ΣwⱼCⱼ", "ważona\nsuma", "Priorytety\nzadań?", GRAY1),
        ("Lmax", "max\nopóźnienie", "Najgorsze\nspóźnienie?", GRAY2),
        ("ΣTⱼ", "suma\nspóźnień", "Łączne\nspóźnienia?", GRAY4),
        ("ΣUⱼ", "liczba\nspóźnionych", "Ile spóźnionych\nzadań?", GRAY1),
    ]

    start_y3 = 4.5
    box_h_g = 1.4
    col_w_g = 1.5

    for i, (symbol, label, question, fill) in enumerate(gamma_items):
        x = start_x + i * col_w_g
        y = start_y3
        rect = FancyBboxPatch(
            (x, y),
            col_w_g - 0.1,
            box_h_g,
            boxstyle="round,pad=0.04",
            lw=1,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            x + (col_w_g - 0.1) / 2,
            y + box_h_g - 0.1,
            symbol,
            ha="center",
            va="top",
            fontsize=9,
            fontweight="bold",
        )
        ax.text(
            x + (col_w_g - 0.1) / 2,
            y + box_h_g / 2 - 0.05,
            label,
            ha="center",
            va="center",
            fontsize=6,
        )
        ax.text(
            x + (col_w_g - 0.1) / 2,
            y + 0.15,
            f'„{question}"',
            ha="center",
            va="bottom",
            fontsize=5,
            style="italic",
        )

    # === BOTTOM: Example + Optimal methods ===
    ex_y = 3.5
    ax.text(
        0.3,
        ex_y,
        "Przykłady zapisu i optymalne metody:",
        fontsize=8,
        fontweight="bold",
        va="top",
    )

    examples = [
        ("1 || ΣCⱼ", "SPT (najkrótsze\nnajpierw)", "O(n log n)", GRAY1),
        ("1 || Lmax", "EDD (najwcześniejszy\ntermin)", "O(n log n)", GRAY4),
        ("F2 || Cmax", "Algorytm\nJohnsona", "O(n log n)", GRAY2),
        ("Pm || Cmax", "LPT heurystyka\n(NP-trudny!)", "NP-hard", GRAY3),
        ("Jm || Cmax", "Branch & Bound\n(NP-trudny!)", "NP-hard", GRAY5),
    ]

    ex_start_y = 1.8
    ex_box_w = 1.72
    ex_box_h = 1.4

    for i, (notation, method, complexity, fill) in enumerate(examples):
        x = start_x + i * (ex_box_w + 0.1)
        y = ex_start_y
        rect = FancyBboxPatch(
            (x, y),
            ex_box_w,
            ex_box_h,
            boxstyle="round,pad=0.04",
            lw=1.2,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            x + ex_box_w / 2,
            y + ex_box_h - 0.12,
            notation,
            ha="center",
            va="top",
            fontsize=8,
            fontweight="bold",
            fontfamily="monospace",
        )
        ax.text(
            x + ex_box_w / 2,
            y + ex_box_h / 2 - 0.05,
            method,
            ha="center",
            va="center",
            fontsize=6,
        )
        ax.text(
            x + ex_box_w / 2,
            y + 0.12,
            complexity,
            ha="center",
            va="bottom",
            fontsize=6.5,
            fontweight="bold",
            color="#555555",
        )

    # Footer mnemonic summary
    ax.text(
        5.0,
        0.8,
        '„\u03b1|β|\u03b3 = Maszyny | Ograniczenia | Cel"',
        ha="center",
        fontsize=9,
        fontweight="bold",
        style="italic",
        color="#333333",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
            "lw": 1,
        },
    )

    ax.text(
        5.0,
        0.2,
        "\u03b1: ILE maszyn i JAKIE?    "
        "β: JAKIE ograniczenia zadań?    "
        "\u03b3: CO minimalizujemy?",
        ha="center",
        fontsize=7,
        color="#555555",
    )

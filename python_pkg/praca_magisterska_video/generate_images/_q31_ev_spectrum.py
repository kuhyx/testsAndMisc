"""Q31 Diagrams 5 & 6: Expected value + decision conditions spectrum."""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._q31_common import (
    _WINNING_EV,
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    LN,
    OUTPUT_DIR,
    _logger,
)


def draw_expected_value() -> None:
    """Draw expected value criterion with probability-weighted bars."""
    fig, axes = plt.subplots(1, 3, figsize=(8.27, 3.5), sharey=True)
    fig.suptitle(
        "Kryterium wartości oczekiwanej E[X] \u2014 rozkład wyników per alternatywa",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    probs = [0.5, 0.3, 0.2]
    alts = [
        ("A₁ (fabryka)", [200, 50, -100], 95),
        ("A₂ (sklep)", [80, 70, 40], 69),
        ("A₃ (obligacje)", [30, 30, 30], 30),
    ]

    hatches = ["///", "...", "xxx"]

    for _idx, (ax, (name, vals, ev)) in enumerate(zip(axes, alts, strict=False)):
        x_positions = [0, 0.6, 1.0]
        widths = [p * 0.9 for p in probs]

        for i, (v, p, h) in enumerate(zip(vals, probs, hatches, strict=False)):
            color = "white" if v >= 0 else GRAY2
            ax.bar(
                x_positions[i],
                v,
                width=widths[i],
                color=color,
                edgecolor=LN,
                hatch=h,
                lw=0.8,
                align="edge",
            )
            offset = 8 if v >= 0 else -12
            ax.text(
                x_positions[i] + widths[i] / 2,
                v + offset,
                f"{v}",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
            )
            contrib = v * p
            ax.text(
                x_positions[i] + widths[i] / 2,
                v / 2,
                f"{v}x{p}\n={contrib:.0f}",
                ha="center",
                va="center",
                fontsize=6,
                style="italic",
            )

        # Expected value line
        ax.axhline(y=ev, color=LN, lw=2, ls="--")
        ax.text(
            1.35,
            ev,
            f"E[X]={ev}",
            fontsize=8,
            fontweight="bold",
            va="center",
            ha="left",
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": GRAY1,
                "edgecolor": LN,
            },
        )

        ax.set_title(name, fontsize=9, fontweight="bold")
        ax.set_xticks([0.225, 0.735, 1.09])
        ax.set_xticklabels(["S₁", "S₂", "S₃"], fontsize=7)
        ax.axhline(y=0, color=LN, lw=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(labelsize=7)

        # Star on winner
        if ev == _WINNING_EV:
            ax.text(
                0.7,
                ev + 20,
                "★ MAX",
                fontsize=9,
                fontweight="bold",
                ha="center",
                va="bottom",
            )

    axes[0].set_ylabel("Wypłata (tys. zł)", fontsize=8)

    plt.tight_layout()
    outpath = str(Path(OUTPUT_DIR) / "q31_expected_value.png")
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", outpath)


def draw_conditions_spectrum() -> None:
    """Draw decision conditions spectrum diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Warunki decyzyjne \u2014 spektrum wiedzy decydenta",
        fontsize=FS_TITLE + 1,
        fontweight="bold",
        pad=10,
    )

    # Three zones
    zones = [
        (
            0.3,
            1.5,
            2.8,
            2.5,
            "PEWNOŚĆ",
            "white",
            [
                "Znamy dokładny wynik",
                "Przykład: lokata 5%",
                "Metoda: po prostu wybierz",
                "najlepszy wynik",
            ],
        ),
        (
            3.5,
            1.5,
            2.8,
            2.5,
            "RYZYKO",
            GRAY1,
            [
                "Znamy wyniki I prawdop.",
                "Przykład: gra w kości",
                "Metoda: wartość",
                "oczekiwana E[X]",
            ],
        ),
        (
            6.7,
            1.5,
            2.8,
            2.5,
            "NIEPEWNOŚĆ",
            GRAY3,
            [
                "Znamy wyniki, ale",
                "NIE znamy prawdop.",
                "Metody: Laplace, maximax,",
                "maximin, Hurwicz, Savage",
            ],
        ),
    ]

    for x, y, w, h, title, fill, lines in zones:
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.1",
            lw=2,
            edgecolor=LN,
            facecolor=fill,
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2,
            y + h - 0.3,
            title,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
        )
        for i, line in enumerate(lines):
            ax.text(
                x + w / 2,
                y + h - 0.7 - i * 0.4,
                line,
                ha="center",
                va="center",
                fontsize=7,
            )

    # Arrows between zones
    ax.annotate(
        "",
        xy=(3.4, 2.75),
        xytext=(3.15, 2.75),
        arrowprops={"arrowstyle": "->", "color": LN, "lw": 2},
    )
    ax.annotate(
        "",
        xy=(6.6, 2.75),
        xytext=(6.35, 2.75),
        arrowprops={"arrowstyle": "->", "color": LN, "lw": 2},
    )

    # Bottom: knowledge gradient bar
    gradient_y = 0.5
    gradient_h = 0.5
    n_steps = 50
    for i in range(n_steps):
        x = 0.3 + i * (9.2 / n_steps)
        w = 9.2 / n_steps + 0.01
        gray_val = 1 - (i / n_steps) * 0.7
        rect = mpatches.Rectangle(
            (x, gradient_y),
            w,
            gradient_h,
            lw=0,
            facecolor=str(gray_val),
        )
        ax.add_patch(rect)

    rect = mpatches.Rectangle(
        (0.3, gradient_y),
        9.2,
        gradient_h,
        lw=1.5,
        edgecolor=LN,
        facecolor="none",
    )
    ax.add_patch(rect)

    ax.text(
        0.3,
        gradient_y - 0.15,
        "Dużo wiedzy",
        fontsize=7,
        ha="left",
        va="top",
    )
    ax.text(
        9.5,
        gradient_y - 0.15,
        "Mało wiedzy",
        fontsize=7,
        ha="right",
        va="top",
    )
    ax.text(
        4.95,
        gradient_y + gradient_h / 2,
        "POZIOM WIEDZY DECYDENTA",
        fontsize=8,
        fontweight="bold",
        ha="center",
        va="center",
        color="white",
    )

    plt.tight_layout()
    outpath = str(Path(OUTPUT_DIR) / "q31_conditions_spectrum.png")
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", outpath)

"""Q31 Diagrams 3 & 4: Hurwicz interpolation + criteria mnemonic map."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import numpy as np

from python_pkg.praca_magisterska_video.generate_images._q31_common import (
    BG,
    DPI,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    LN,
    OUTPUT_DIR,
    _logger,
    draw_box,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def draw_hurwicz_interpolation() -> None:
    """Draw Hurwicz alpha interpolation diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 4))
    ax.set_title(
        "Kryterium Hurwicza \u2014 wpływ \u03b1 na wybór alternatywy",
        fontsize=FS_TITLE + 1,
        fontweight="bold",
        pad=10,
    )

    alphas = np.linspace(0, 1, 200)

    v1 = alphas * 200 + (1 - alphas) * (-100)
    v2 = alphas * 80 + (1 - alphas) * 40
    v3 = alphas * 30 + (1 - alphas) * 30

    ax.plot(
        alphas,
        v1,
        "k-",
        lw=2,
        label="A₁ (fabryka): V = 300\u03b1 - 100",
    )
    ax.plot(
        alphas,
        v2,
        "k--",
        lw=2,
        label="A₂ (sklep): V = 40\u03b1 + 40",
    )
    ax.plot(
        alphas,
        v3,
        "k:",
        lw=2,
        label="A₃ (obligacje): V = 30",
    )

    # Crossover A2=A1
    alpha_cross_12 = 140 / 260
    v_cross_12 = 40 * alpha_cross_12 + 40

    ax.plot(alpha_cross_12, v_cross_12, "ko", markersize=8, zorder=5)
    ax.annotate(
        f"\u03b1 ≈ {alpha_cross_12:.2f}\nA₁ = A₂",
        xy=(alpha_cross_12, v_cross_12),
        xytext=(alpha_cross_12 + 0.12, v_cross_12 - 30),
        fontsize=8,
        fontweight="bold",
        arrowprops={
            "arrowstyle": "->",
            "color": LN,
            "lw": 1,
        },
    )

    # Shade winning regions
    ax.axvspan(0, alpha_cross_12, alpha=0.08, color="black")
    ax.axvspan(alpha_cross_12, 1, alpha=0.15, color="black")

    ax.text(
        alpha_cross_12 / 2,
        -60,
        "A₂ wygrywa\n(pesymistycznie)",
        fontsize=8,
        ha="center",
        va="center",
        bbox={
            "boxstyle": "round",
            "facecolor": "white",
            "edgecolor": LN,
        },
    )
    ax.text(
        (alpha_cross_12 + 1) / 2,
        160,
        "A₁ wygrywa\n(optymistycznie)",
        fontsize=8,
        ha="center",
        va="center",
        bbox={
            "boxstyle": "round",
            "facecolor": "white",
            "edgecolor": LN,
        },
    )

    # Special alpha values
    ax.axvline(x=0, color=LN, lw=0.5, ls=":")
    ax.axvline(x=1, color=LN, lw=0.5, ls=":")
    ax.text(
        0,
        -115,
        "\u03b1=0\nmaximin",
        fontsize=7,
        ha="center",
        va="top",
        fontweight="bold",
    )
    ax.text(
        1,
        -115,
        "\u03b1=1\nmaximax",
        fontsize=7,
        ha="center",
        va="top",
        fontweight="bold",
    )

    ax.set_xlabel("Współczynnik optymizmu \u03b1", fontsize=9)
    ax.set_ylabel("V(Aᵢ) = \u03b1·max + (1-\u03b1)·min", fontsize=9)
    ax.legend(fontsize=8, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(-0.05, 1.05)
    ax.axhline(y=0, color=LN, lw=0.3, ls="-")
    ax.tick_params(labelsize=8)

    plt.tight_layout()
    outpath = str(Path(OUTPUT_DIR) / "q31_hurwicz_alpha.png")
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", outpath)


def _draw_mnemonic_criteria_boxes(ax: Axes) -> None:
    """Draw the 6 criteria boxes around the center."""
    criteria = [
        (
            0,
            6.5,
            3,
            1.2,
            "WARTOŚĆ OCZEKIWANA",
            "\u201eMam prawdopodobieństwa\u201d",
            "E[Aᵢ] = Σ pⱼ·aᵢⱼ",
        ),
        (
            3.5,
            6.5,
            3,
            1.2,
            "LAPLACE",
            "\u201eWszystko po równo\u201d",
            "V = Σaᵢⱼ / n",
        ),
        (
            7,
            6.5,
            3,
            1.2,
            "MAXIMAX",
            "\u201eOptymista: max z max\u201d",
            "max maxⱼ aᵢⱼ",
        ),
        (
            0,
            0.5,
            3,
            1.2,
            "MAXIMIN (Wald)",
            "\u201ePesymista: max z min\u201d",
            "max minⱼ aᵢⱼ",
        ),
        (
            3.5,
            0.5,
            3,
            1.2,
            "HURWICZ",
            "\u201e\u03b1 pomiędzy\u201d",
            "\u03b1·max + (1-\u03b1)·min",
        ),
        (
            7,
            0.5,
            3,
            1.2,
            "SAVAGE",
            "\u201eMin max żalu\u201d",
            "min maxⱼ rᵢⱼ",
        ),
    ]

    fills = [GRAY3, GRAY1, "white", "white", GRAY1, GRAY3]

    for i, (x, y, w, h, title, mnem, formula) in enumerate(criteria):
        rect = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.08",
            lw=1.5,
            edgecolor=LN,
            facecolor=fills[i],
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2,
            y + h * 0.78,
            title,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
        )
        ax.text(
            x + w / 2,
            y + h * 0.45,
            mnem,
            ha="center",
            va="center",
            fontsize=7,
            style="italic",
        )
        ax.text(
            x + w / 2,
            y + h * 0.15,
            formula,
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
            family="monospace",
        )

        # Arrows from center to each box
        cx, cy = 5, 4
        bx = x + w / 2
        by_center = y + h / 2
        if by_center > cy:
            ax.annotate(
                "",
                xy=(bx, y),
                xytext=(cx, 4.5),
                arrowprops={
                    "arrowstyle": "->",
                    "color": LN,
                    "lw": 1,
                    "connectionstyle": "arc3,rad=0",
                },
            )
        else:
            ax.annotate(
                "",
                xy=(bx, y + h),
                xytext=(cx, 3.5),
                arrowprops={
                    "arrowstyle": "->",
                    "color": LN,
                    "lw": 1,
                    "connectionstyle": "arc3,rad=0",
                },
            )

    # Labels on arrows
    arrow_labels = [
        (1.2, 5.6, "znane p"),
        (5, 5.6, "p = 1/n"),
        (8.7, 5.6, "max ↑"),
        (1.2, 2.5, "min ↑"),
        (5, 2.5, "podaj \u03b1"),
        (8.7, 2.5, "macierz\nżalu"),
    ]
    for lx, ly, ltext in arrow_labels:
        ax.text(
            lx,
            ly,
            ltext,
            fontsize=7,
            ha="center",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": "white",
                "edgecolor": GRAY3,
                "lw": 0.5,
            },
        )


def draw_criteria_mnemonic() -> None:
    """Draw decision criteria mnemonic map diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(8.27, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Mapa mnemoniczna \u2014 6 kryteriów decyzyjnych",
        fontsize=FS_TITLE + 2,
        fontweight="bold",
        pad=10,
    )

    # Central node
    draw_box(
        ax,
        3.5,
        3.5,
        3,
        1,
        "MACIERZ\nWYPŁAT",
        fill=GRAY2,
        lw=2,
        fontsize=11,
        fontweight="bold",
    )

    _draw_mnemonic_criteria_boxes(ax)

    plt.tight_layout()
    outpath = str(Path(OUTPUT_DIR) / "q31_criteria_mnemonic.png")
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", outpath)

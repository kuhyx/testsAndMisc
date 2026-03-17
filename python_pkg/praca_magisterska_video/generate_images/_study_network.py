"""Network models and vector clock diagrams."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_study_diagrams import (
    BG,
    DPI,
    FS,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    OUTPUT_DIR,
    draw_box,
)

_logger = logging.getLogger(__name__)


def draw_network_models() -> None:
    """Draw network models."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Sieciowe modele optymalizacji"
        " — \u201eNasz Ma\u0142y Miko\u0142aj Przydzieli\u0142"
        " Trasy Ci\u0119\u017car\u00f3wkom Mapuj\u0105c\u201d",
        fontsize=10,
        fontweight="bold",
        pad=10,
    )

    models = [
        (
            1,
            "Najkrótsza\nścieżka",
            "GPS, routing\nDijkstra, A*",
            "A→B najszybciej?",
            GRAY1,
        ),
        (
            2,
            "Maksymalny\nprzepływ",
            "Przepustowość\nFord-Fulkerson",
            "Ile max przesłać?",
            GRAY4,
        ),
        (
            3,
            "Min koszt\nprzepływu",
            "Najtańszy transport\nSieciowy simpleks",
            "X jednostek najtaniej?",
            GRAY4,
        ),
        (
            4,
            "Przydział\n(assignment)",
            "n→n, min koszt\nAlg. Węgierski O(n³)",
            "Kto robi co?",
            GRAY2,
        ),
        (
            5,
            "TSP\n(komiwojażer)",
            "Objazd miast\nNP-trudny, heurystyki",
            "Objazd wszystkiego?",
            GRAY3,
        ),
        (6, "CPM/PERT", "Harmonogram\nŚcieżka krytyczna", "Ile trwa projekt?", GRAY2),
        (
            7,
            "MST\n(drzewo rozp.)",
            "Min połączenie\nKruskal, Prim",
            "Połącz najtaniej?",
            GRAY1,
        ),
    ]

    # Layout: 3 pairs + 1, arranged in labeled groups
    group_positions = [
        ("DROGI", [(0, 0.3, 4.0), (6, 0.3, 1.5)]),
        ("PRZEPŁYW", [(1, 3.3, 4.0), (2, 3.3, 1.5)]),
        ("ZARZĄDZANIE", [(3, 6.3, 4.0), (5, 6.3, 1.5)]),
    ]

    box_w = 2.6
    box_h = 1.8

    for group_label, items in group_positions:
        xs = [x for _, x, y in items]
        ys = [y for _, x, y in items]
        gx = min(xs) - 0.15
        gy = min(ys) - 0.3
        gw = box_w + 0.3
        gh = max(ys) - min(ys) + box_h + 0.6
        rect = mpatches.FancyBboxPatch(
            (gx, gy),
            gw,
            gh,
            boxstyle="round,pad=0.1",
            lw=0.8,
            edgecolor=GRAY3,
            facecolor="white",
            linestyle="--",
        )
        ax.add_patch(rect)
        ax.text(
            gx + gw / 2,
            gy + gh + 0.12,
            group_label,
            ha="center",
            fontsize=8,
            fontweight="bold",
            color="#555555",
        )

        for idx, x, y in items:
            num, name, detail, question, fill = models[idx]
            draw_box(ax, x, y, box_w, box_h, "", fill=fill, fontsize=FS)
            ax.text(
                x + box_w / 2,
                y + box_h - 0.25,
                f"{num}. {name}",
                ha="center",
                va="top",
                fontsize=8,
                fontweight="bold",
            )
            ax.text(
                x + box_w / 2,
                y + box_h / 2 - 0.1,
                detail,
                ha="center",
                va="center",
                fontsize=7,
            )
            ax.text(
                x + box_w / 2,
                y + 0.2,
                f'→ „{question}"',
                ha="center",
                va="bottom",
                fontsize=6.5,
                style="italic",
            )

    # TSP alone at bottom center
    idx = 4
    x, y = 4.5, -0.1
    num, name, detail, question, fill = models[idx]
    rect = mpatches.FancyBboxPatch(
        (x - 0.15, y - 0.15),
        box_w + 0.3,
        box_h + 0.3,
        boxstyle="round,pad=0.1",
        lw=0.8,
        edgecolor=GRAY3,
        facecolor="white",
        linestyle="--",
    )
    ax.add_patch(rect)
    ax.text(
        x + box_w / 2,
        y + box_h + 0.3,
        "SAM (NP-trudny)",
        ha="center",
        fontsize=8,
        fontweight="bold",
        color="#555555",
    )
    draw_box(ax, x, y, box_w, box_h, "", fill=fill, fontsize=FS)
    ax.text(
        x + box_w / 2,
        y + box_h - 0.25,
        f"{num}. {name}",
        ha="center",
        va="top",
        fontsize=8,
        fontweight="bold",
    )
    ax.text(
        x + box_w / 2, y + box_h / 2 - 0.1, detail, ha="center", va="center", fontsize=7
    )
    ax.text(
        x + box_w / 2,
        y + 0.2,
        f'→ „{question}"',
        ha="center",
        va="bottom",
        fontsize=6.5,
        style="italic",
    )

    ax.set_ylim(-0.5, 7.2)

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "network_models_mnemonic.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ network_models_mnemonic.png")


def draw_vector_clock_timeline() -> None:
    """Draw vector clock timeline."""
    _fig, ax = plt.subplots(1, 1, figsize=(8.27, 4.5))
    ax.set_xlim(-0.5, 11)
    ax.set_ylim(-0.5, 4.5)
    ax.axis("off")
    ax.set_title(
        "Zegary wektorowe — przykład z 3 procesami",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Process lines
    procs = [("P₁", 3.5), ("P₂", 2.0), ("P₃", 0.5)]
    for name, y in procs:
        ax.plot([0.5, 10.5], [y, y], color="black", lw=1.5)
        ax.text(0.1, y, name, ha="right", va="center", fontsize=10, fontweight="bold")

    # Events
    events = [
        ("A", 3.5, 1.5, "[1,0,0]", GRAY1),
        ("B", 2.0, 2.5, "[0,1,0]", GRAY2),
        ("C", 2.0, 5.0, "[1,2,0]", GRAY2),
        ("D", 0.5, 4.0, "[0,0,1]", GRAY3),
        ("E", 3.5, 6.5, "[2,0,0]", GRAY1),
        ("F", 2.0, 8.0, "[2,3,0]", GRAY2),
    ]

    for name, y, x, vec, fill in events:
        circle = plt.Circle((x, y), 0.25, facecolor=fill, edgecolor="black", lw=1.5)
        ax.add_patch(circle)
        ax.text(x, y, name, ha="center", va="center", fontsize=9, fontweight="bold")
        ax.text(
            x,
            y + 0.45,
            vec,
            ha="center",
            va="bottom",
            fontsize=7,
            fontfamily="monospace",
            color="#333333",
        )

    # Messages (arrows between processes)
    ax.annotate(
        "",
        xy=(4.75, 2.0),
        xytext=(1.75, 3.5),
        arrowprops={
            "arrowstyle": "->",
            "color": "#444444",
            "lw": 1.5,
            "connectionstyle": "arc3,rad=0.05",
        },
    )
    ax.text(3.0, 3.0, "msg₁", ha="center", fontsize=7, color="#444444", style="italic")

    ax.annotate(
        "",
        xy=(7.75, 2.0),
        xytext=(6.75, 3.5),
        arrowprops={
            "arrowstyle": "->",
            "color": "#444444",
            "lw": 1.5,
            "connectionstyle": "arc3,rad=0.05",
        },
    )
    ax.text(7.0, 3.0, "msg₂", ha="center", fontsize=7, color="#444444", style="italic")

    # Concurrency annotations
    ax.annotate(
        "A ∥ B\n(współbieżne)",
        xy=(2.0, 1.2),
        fontsize=7,
        ha="center",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )
    ax.annotate(
        "C ∥ D\n(współbieżne)",
        xy=(4.5, 0.9),
        fontsize=7,
        ha="center",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY4, "edgecolor": GRAY5},
    )
    ax.annotate(
        "A → C\n(przyczynowe)",
        xy=(3.3, 4.2),
        fontsize=7,
        ha="center",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": GRAY1, "edgecolor": GRAY3},
    )

    # Time arrow
    ax.annotate(
        "",
        xy=(10.5, -0.3),
        xytext=(0.5, -0.3),
        arrowprops={"arrowstyle": "->", "color": GRAY3, "lw": 1.0},
    )
    ax.text(5.5, -0.45, "czas →", ha="center", fontsize=8, color="#777777")

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "vector_clock_timeline.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ vector_clock_timeline.png")

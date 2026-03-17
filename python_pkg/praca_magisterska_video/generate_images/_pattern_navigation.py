"""Pattern language navigation diagram."""

from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
    BG,
    DPI,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    LN,
    OUTPUT_DIR,
)

_logger = logging.getLogger(__name__)

# ============================================================
# 5. Pattern Language Navigation Graph
# ============================================================
def generate_pattern_language_navigation() -> None:
    """Generate pattern language navigation graph diagram."""
    fig, ax = plt.subplots(figsize=(8.27, 9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 12)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_title(
        "Język wzorców \u2014 nawigacja"
        " \u201eproblem \u2192 wzorzec"
        " \u2192 nowy problem\u201d",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=15,
    )

    # Node positions: (x, y, label, is_pattern, fill)
    nodes = [
        (1.5, 10.5, "Monolith\nnie skaluje się", False, "white"),
        (
            1.5, 8.2,
            "Jak routować\nżądania do\nserwisów?",
            False, "white",
        ),
        (
            1.5, 5.9,
            "Co gdy serwis\nnie odpowiada?",
            False, "white",
        ),
        (
            1.5, 3.6,
            "Jak zachować\nspójność\ntransakcji?",
            False, "white",
        ),
        (
            1.5, 1.3,
            "Jak odnaleźć\nadres serwisu?",
            False, "white",
        ),
        (7.0, 9.3, "Microservices", True, GRAY2),
        (7.0, 7.0, "API Gateway", True, GRAY2),
        (7.0, 4.7, "Circuit Breaker", True, GRAY2),
        (7.0, 2.4, "Saga", True, GRAY2),
        (10.0, 5.9, "Service\nDiscovery", True, GRAY1),
    ]

    # Draw nodes
    node_w_prob = 2.8
    node_h_prob = 1.3
    node_w_pat = 2.5
    node_h_pat = 1.0

    for nx, ny, label, is_pattern, fill in nodes:
        if is_pattern:
            w, h = node_w_pat, node_h_pat
            rect = FancyBboxPatch(
                (nx - w / 2, ny - h / 2),
                w,
                h,
                boxstyle="round,pad=0.1",
                lw=2,
                edgecolor=LN,
                facecolor=fill,
            )
            ax.add_patch(rect)
            ax.text(
                nx,
                ny,
                label,
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
            )
        else:
            w, h = node_w_prob, node_h_prob
            rect = FancyBboxPatch(
                (nx - w / 2, ny - h / 2),
                w,
                h,
                boxstyle="round,pad=0.1",
                lw=1.2,
                edgecolor=LN,
                facecolor=fill,
                linestyle="--",
            )
            ax.add_patch(rect)
            ax.text(
                nx,
                ny,
                label,
                ha="center",
                va="center",
                fontsize=FS_SMALL,
                fontstyle="italic",
            )

    # Arrows: problem -> pattern, pattern -> problem
    arrows = [
        (2.9, 10.5, 5.75, 9.5, "rozwiązuje →", "->", 1.5),
        (7.0, 8.8, 2.9, 8.5, "← rodzi problem", "->", 1.0),
        (2.9, 8.0, 5.75, 7.2, "rozwiązuje →", "->", 1.5),
        (7.0, 6.5, 2.9, 6.2, "← rodzi problem", "->", 1.0),
        (2.9, 5.7, 5.75, 5.0, "rozwiązuje →", "->", 1.5),
        (7.0, 4.2, 2.9, 3.9, "← rodzi problem", "->", 1.0),
        (2.9, 3.3, 5.75, 2.6, "rozwiązuje →", "->", 1.5),
        (8.25, 9.0, 9.5, 6.5, "wymaga →", "->", 1.0),
        (2.9, 1.3, 8.75, 5.6, "rozwiązuje →", "->", 1.2),
    ]

    for x1, y1, x2, y2, label, style, lw in arrows:
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops={
                "arrowstyle": style,
                "color": LN,
                "lw": lw,
                "connectionstyle": "arc3,rad=0.05",
            },
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mx,
            my + 0.2,
            label,
            ha="center",
            va="center",
            fontsize=6.5,
            fontstyle="italic",
            color="#555555",
            bbox={
                "boxstyle": "round,pad=0.1",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.8,
            },
        )

    # Legend
    legend_y = 0.3
    r1 = FancyBboxPatch(
        (1.0, legend_y - 0.2),
        1.5,
        0.4,
        boxstyle="round,pad=0.05",
        lw=1,
        edgecolor=LN,
        facecolor="white",
        linestyle="--",
    )
    ax.add_patch(r1)
    ax.text(
        1.75, legend_y, "Problem",
        ha="center", va="center", fontsize=7,
    )
    r2 = FancyBboxPatch(
        (3.5, legend_y - 0.2),
        1.5,
        0.4,
        boxstyle="round,pad=0.05",
        lw=1.5,
        edgecolor=LN,
        facecolor=GRAY2,
    )
    ax.add_patch(r2)
    ax.text(
        4.25,
        legend_y,
        "Wzorzec",
        ha="center",
        va="center",
        fontsize=7,
        fontweight="bold",
    )
    ax.text(
        6.5,
        legend_y,
        "Nawigacja: Problem \u2192 Wzorzec"
        " \u2192 Nowy Problem \u2192 Wzorzec \u2192 ...",
        ha="left",
        va="center",
        fontsize=7,
        fontstyle="italic",
    )

    fig.tight_layout()
    out = str(
        Path(OUTPUT_DIR) / "q14_pattern_language_navigation.png"
    )
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    _logger.info("  Saved: %s", out)


# ============================================================
# Main
# ============================================================

"""Bellman-Ford negative weight and cycle diagrams."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
    BG,
    DPI,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY3,
    GRAY4,
    LIGHT_GREEN,
    LIGHT_RED,
    LIGHT_YELLOW,
    LN,
    NEG_EDGES,
    NEG_POS,
    OUTPUT_DIR,
    draw_neg_graph,
)

_logger = logging.getLogger(__name__)



def _add_annotation_box(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    *,
    color: str,
    bg_color: str,
) -> None:
    """Add a small annotation box near a node."""
    ax.text(
        x,
        y,
        text,
        fontsize=FS_SMALL,
        color=color,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.1",
            "facecolor": bg_color,
            "edgecolor": color,
            "alpha": 0.9,
            "lw": 0.5,
        },
    )


def generate_bf_negative_weights() -> None:
    """Generate two-row figure.

    Row 1: Graph structure + Dijkstra WRONG + Bellman-Ford CORRECT
    Row 2: B-F iterations 1-3 step by step.
    """
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(
        "Bellman-Ford \u2014 ujemne wagi vs Dijkstra\n"
        "Graf: S\u2192A(2), A\u2192C(3),"
        " S\u2192B(5), B\u2192A(-4). Start = S",
        fontsize=FS_TITLE + 1,
        fontweight="bold",
        y=0.99,
    )

    # Row 1: Graph + Dijkstra wrong + BF correct

    # Panel 1: The graph structure
    ax1 = fig.add_subplot(2, 3, 1)
    draw_neg_graph(
        ax1,
        NEG_EDGES,
        title=(
            "Graf z ujemną wagą\n"
            "(B→A = -4, zaznaczona na czerwono)"
        ),
        dist={"S": "0", "A": "?", "B": "?", "C": "?"},
    )
    ax1.annotate(
        "START",
        xy=(NEG_POS["S"][0] - 0.35, NEG_POS["S"][1]),
        xytext=(NEG_POS["S"][0] - 1.2, NEG_POS["S"][1]),
        fontsize=FS,
        fontweight="bold",
        color="#D32F2F",
        arrowprops={
            "arrowstyle": "->",
            "color": "#D32F2F",
            "lw": 2,
        },
        va="center",
    )

    # Panel 2: Dijkstra — WRONG
    ax2 = fig.add_subplot(2, 3, 2)
    draw_neg_graph(
        ax2,
        NEG_EDGES,
        title=(
            "Dijkstra \u2014 BŁĘDNY wynik\n"
            "A zamknięty z d=2, nie poprawia przy B→A"
        ),
        dist={"S": "0", "A": "2", "B": "5", "C": "5"},
        visited={"S", "A", "B", "C"},
        error_nodes={"A", "C"},
    )
    _add_annotation_box(
        ax2,
        NEG_POS["A"][0] + 0.6,
        NEG_POS["A"][1] + 0.3,
        "✗ powinno 1",
        color="#D32F2F",
        bg_color=LIGHT_RED,
    )
    _add_annotation_box(
        ax2,
        NEG_POS["C"][0] + 0.05,
        NEG_POS["C"][1] + 0.55,
        "✗ powinno 4",
        color="#D32F2F",
        bg_color=LIGHT_RED,
    )

    # Panel 3: Bellman-Ford — CORRECT
    ax3 = fig.add_subplot(2, 3, 3)
    draw_neg_graph(
        ax3,
        NEG_EDGES,
        title=(
            "Bellman-Ford \u2014 POPRAWNY wynik\n"
            "Ujemna waga B→A poprawnie propagowana"
        ),
        dist={"S": "0", "A": "1", "B": "5", "C": "4"},
        visited={"S", "A", "B", "C"},
        relaxed_edges={("B", "A")},
    )
    _add_annotation_box(
        ax3,
        NEG_POS["A"][0] + 0.6,
        NEG_POS["A"][1] + 0.3,
        "✓ poprawne!",
        color="#006400",
        bg_color=LIGHT_GREEN,
    )
    _add_annotation_box(
        ax3,
        NEG_POS["C"][0] + 0.05,
        NEG_POS["C"][1] + 0.55,
        "✓ poprawne!",
        color="#006400",
        bg_color=LIGHT_GREEN,
    )

    # Row 2: B-F iterations step by step
    iterations = [
        {
            "title": (
                "B-F Iteracja 1\n"
                "Relaksuj WSZYSTKIE krawędzie"
            ),
            "dist": {
                "S": "0", "A": "1", "B": "5", "C": "5",
            },
            "relaxed": {
                ("S", "A"), ("A", "C"),
                ("S", "B"), ("B", "A"),
            },
            "detail": (
                "S→A: 0+2=2<∞ → A=2\n"
                "A→C: 2+3=5<∞ → C=5\n"
                "S→B: 0+5=5<∞ → B=5\n"
                "B→A: 5-4=1<2 → A=1 ✓"
            ),
        },
        {
            "title": (
                "B-F Iteracja 2\n"
                "Propagacja poprawionego A"
            ),
            "dist": {
                "S": "0", "A": "1", "B": "5", "C": "4",
            },
            "relaxed": {("A", "C")},
            "detail": (
                "S→A: 0+2=2>1 ✗\n"
                "A→C: 1+3=4<5 → C=4 ✓\n"
                "S→B: 0+5=5=5 ✗\n"
                "B→A: 5-4=1=1 ✗"
            ),
        },
        {
            "title": (
                "B-F Iteracja 3\n"
                "Brak zmian → stabilne!"
            ),
            "dist": {
                "S": "0", "A": "1", "B": "5", "C": "4",
            },
            "relaxed": set(),
            "detail": (
                "Wszystkie krawędzie:\n"
                "brak poprawy ✗\n"
                "→ wynik stabilny\n"
                "→ BRAK cyklu ujemnego"
            ),
        },
    ]

    for i, it in enumerate(iterations):
        ax = fig.add_subplot(2, 3, i + 4)
        draw_neg_graph(
            ax,
            NEG_EDGES,
            title=it["title"],
            dist=it["dist"],
            visited={"S", "A", "B", "C"},
            relaxed_edges=it["relaxed"],
        )
        ax.text(
            3.2,
            -0.5,
            it["detail"],
            ha="center",
            va="top",
            fontsize=FS_SMALL,
            family="monospace",
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": GRAY4,
                "edgecolor": GRAY3,
            },
        )

    # Bottom note
    fig.text(
        0.5,
        0.01,
        "Dijkstra zamyka wierzchołki na stałe"
        " (zachłanność) → ujemna waga B→A(-4)"
        " nie może poprawić zamkniętego A.\n"
        "Bellman-Ford relaksuje WSZYSTKIE krawędzie"
        " w każdej iteracji → ujemne wagi"
        " propagują się poprawnie.",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_YELLOW,
            "edgecolor": LN,
        },
    )

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(
        str(Path(OUTPUT_DIR) / "bellman_ford_negative_weights.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ bellman_ford_negative_weights.png")


def generate_bf_negative_cycle() -> None:
    """Generate figure showing negative cycle detection.

    Graph: S->A(2), A->C(3), S->B(5), B->A(-4), C->B(-3)
    Cycle: B->A->C->B = -4+3+(-3) = -4 < 0.
    """
    fig = plt.figure(figsize=(14, 5.5))
    fig.suptitle(
        "Bellman-Ford \u2014 wykrywanie cyklu ujemnego\n"
        "Dodano krawędź C→B(-3)."
        " Cykl: B→A→C→B = -4+3+(-3) = -4 < 0",
        fontsize=FS_TITLE + 1,
        fontweight="bold",
        y=0.99,
    )

    # Panel 1: Graph with cycle highlighted
    ax1 = fig.add_subplot(1, 3, 1)
    draw_neg_graph(
        ax1,
        NEG_EDGES,
        title=(
            "Graf z cyklem ujemnym\n"
            "Dodana krawędź C→B(-3) \u2014 przerywana"
        ),
        dist={"S": "0", "A": "?", "B": "?", "C": "?"},
        extra_edges=[("C", "B", -3)],
    )
    ax1.annotate(
        "CYKL\n-4+3+(-3)=-4<0",
        xy=(3.3, 2.0),
        fontsize=FS,
        fontweight="bold",
        color="#D32F2F",
        ha="center",
        va="center",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_RED,
            "edgecolor": "#D32F2F",
            "alpha": 0.9,
        },
    )

    # Panel 2: After V-1 iterations — still changing
    ax2 = fig.add_subplot(1, 3, 2)
    draw_neg_graph(
        ax2,
        NEG_EDGES,
        title=(
            "Po V-1=3 iteracjach\n"
            "dist wciąż maleje (niestabilne!)"
        ),
        dist={"S": "0", "A": "-7", "B": "-4", "C": "-4"},
        visited={"S", "A", "B", "C"},
        error_nodes={"A", "B", "C"},
        extra_edges=[("C", "B", -3)],
    )
    ax2.text(
        3.2,
        -0.4,
        "Każde okrążenie cyklu\n"
        "zmniejsza dist o 4.\n"
        "Dist → -∞ (brak minimum!)",
        ha="center",
        va="top",
        fontsize=FS_SMALL,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_RED,
            "edgecolor": "#D32F2F",
        },
    )

    # Panel 3: V-th iteration detects
    ax3 = fig.add_subplot(1, 3, 3)
    ax3.axis("off")
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)

    detection_text = (
        "V-ta iteracja (sprawdzenie):\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "for (src, dst, w) in edges:\n"
        "  if dist[src]+w < dist[dst]:\n"
        "    return None  # CYKL!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Sprawdzamy np. krawędź B→A:\n"
        "  dist[B] + (-4) = -4 + (-4) = -8\n"
        "  -8 < dist[A] = -7\n"
        "  → NADAL SIĘ POPRAWIA!\n"
        "  → CYKL UJEMNY WYKRYTY!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Wynik: return None\n"
        "(najkrótsza ścieżka nie istnieje)"
    )
    ax3.text(
        5,
        5,
        detection_text,
        ha="center",
        va="center",
        fontsize=FS + 0.5,
        family="monospace",
        bbox={
            "boxstyle": "round,pad=0.6",
            "facecolor": LIGHT_RED,
            "edgecolor": "#D32F2F",
            "lw": 2,
        },
    )
    ax3.set_title(
        "Wykrywanie \u2014 V-ta iteracja\n"
        "Jeśli cokolwiek się poprawia → cykl ujemny!",
        fontsize=FS,
        fontweight="bold",
        pad=5,
    )

    # Bottom note
    fig.text(
        0.5,
        0.01,
        "Bez cyklu ujemnego: po V-1 iteracjach"
        " dist jest stabilne. "
        "Z cyklem ujemnym: dist maleje"
        " w nieskończoność"
        " → V-ta iteracja to wykrywa.",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_YELLOW,
            "edgecolor": LN,
        },
    )

    plt.tight_layout(rect=[0, 0.06, 1, 0.94])
    plt.savefig(
        str(Path(OUTPUT_DIR) / "bellman_ford_negative_cycle.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("  ✓ bellman_ford_negative_cycle.png")



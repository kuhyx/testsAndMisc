"""Shortest path traversal diagram generators."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images.generate_shortest_path_diagrams import (
    BG,
    DPI,
    EDGES,
    FS,
    FS_TITLE,
    GRAY3,
    GRAY4,
    LIGHT_BLUE,
    LIGHT_GREEN,
    LN,
    NODE_POS,
    OUTPUT_DIR,
    draw_full_graph,
    draw_graph_edge,
    draw_graph_node,
)

_logger = logging.getLogger(__name__)


# ============================================================
# 1. Graph structure diagram
# ============================================================
def draw_graph_structure() -> None:
    """Draw the shared example graph used across all algorithms."""
    _fig, ax = plt.subplots(1, 1, figsize=(5, 4))
    ax.set_xlim(-0.5, 5.0)
    ax.set_ylim(-1.2, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Przykładowy graf — wspólny dla wszystkich algorytmów\n"
        "Wierzchołki: {A, B, C, D}, Start = A",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Draw edges
    for u, v, w in EDGES:
        draw_graph_edge(ax, NODE_POS[u], NODE_POS[v], w)

    # Draw nodes
    for node_name, pos in NODE_POS.items():
        draw_graph_node(ax, node_name, pos)

    # Start arrow
    ax.annotate(
        "START",
        xy=(NODE_POS["A"][0] - 0.35, NODE_POS["A"][1]),
        xytext=(NODE_POS["A"][0] - 1.2, NODE_POS["A"][1]),
        fontsize=FS,
        fontweight="bold",
        color="#D32F2F",
        arrowprops={"arrowstyle": "->", "color": "#D32F2F", "lw": 2},
        va="center",
    )

    # Edge list
    ax.text(
        2.3,
        -0.8,
        "Krawędzie: A→B(2), A→C(4), B→D(3), C→D(5)\n|V|=4, |E|=4, wagi ≥ 0",
        ha="center",
        va="center",
        fontsize=FS,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "graph_example_structure.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("graph_example_structure.png")


# ============================================================
# 2. Dijkstra traversal
# ============================================================
def draw_dijkstra_traversal() -> None:
    """Draw step-by-step Dijkstra on the shared graph."""
    steps = [
        {
            "title": "Krok 0: Inicjalizacja\nd = {A:0, B:∞, C:∞, D:∞}",
            "dist": {"A": "0", "B": "∞", "C": "∞", "D": "∞"},
            "current": "A",
            "visited": set(),
            "highlighted": set(),
            "relaxed": set(),
        },
        {
            "title": (
                "Krok 1: Przetwarzam A (d=0)\n"
                "Relaksacja: A→B: 0+2=2<∞ ✓"
                "  A→C: 0+4=4<∞ ✓"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "∞"},
            "current": "A",
            "visited": {"A"},
            "highlighted": set(),
            "relaxed": {("A", "B"), ("A", "C")},
        },
        {
            "title": (
                "Krok 2: Przetwarzam B (d=2) — minimum\nRelaksacja: B→D: 2+3=5<∞ ✓"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "5"},
            "current": "B",
            "visited": {"A", "B"},
            "highlighted": set(),
            "relaxed": {("B", "D")},
        },
        {
            "title": (
                "Krok 3: Przetwarzam C (d=4)\n"
                "Relaksacja: C→D: 4+5=9 > 5"
                " ✗ (nie poprawia)"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "5"},
            "current": "C",
            "visited": {"A", "B", "C"},
            "highlighted": {("C", "D")},
            "relaxed": set(),
        },
        {
            "title": (
                "Krok 4: WYNIK — wszystkie przetworzone\nd = {A:0, B:2, C:4, D:5}"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "5"},
            "current": None,
            "visited": {"A", "B", "C", "D"},
            "highlighted": {("A", "B"), ("B", "D"), ("A", "C")},
            "relaxed": set(),
        },
    ]

    fig, axes = plt.subplots(1, 5, figsize=(14, 3.5))
    fig.suptitle(
        "Dijkstra — przejście grafu krok po kroku (zachłannie: zawsze bierz min d)",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=1.02,
    )

    for _i, (ax, step) in enumerate(zip(axes, steps, strict=False)):
        draw_full_graph(
            ax,
            title=step["title"],
            dist=step["dist"],
            current=step["current"],
            visited=step["visited"],
            highlighted_edges=step["highlighted"],
            relaxed_edges=step["relaxed"],
        )

    # Legend
    fig.text(
        0.5,
        -0.04,
        "[zolty] = aktualnie przetwarzany"
        "    [zielony] = odwiedzony (zamkniety)"
        "    czerwona krawedz = relaksacja OK"
        "    szara krawedz = nie poprawia",
        ha="center",
        fontsize=FS,
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": GRAY4,
            "edgecolor": GRAY3,
        },
    )

    plt.tight_layout()
    plt.savefig(
        str(Path(OUTPUT_DIR) / "dijkstra_traversal.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("dijkstra_traversal.png")


# ============================================================
# 3. Bellman-Ford traversal
# ============================================================
def draw_bellman_ford_traversal() -> None:
    """Draw step-by-step Bellman-Ford on the shared graph."""
    fig = plt.figure(figsize=(14, 7))
    fig.suptitle(
        "Bellman-Ford — przejście grafu krok po kroku\n"
        "(V-1 = 3 iteracje, w każdej relaksuj"
        " WSZYSTKIE krawędzie)",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=0.98,
    )

    # Data for each iteration
    iterations = [
        {
            "title": "Inicjalizacja",
            "edges_detail": "—",
            "dist": {"A": "0", "B": "∞", "C": "∞", "D": "∞"},
            "relaxed": set(),
        },
        {
            "title": "Iteracja 1 (V-1=3)",
            "edges_detail": (
                "A→B: 0+2=2<∞ ✓\nA→C: 0+4=4<∞ ✓\nB→D: 2+3=5<∞ ✓\nC→D: 4+5=9>5 ✗"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "5"},
            "relaxed": {("A", "B"), ("A", "C"), ("B", "D")},
        },
        {
            "title": "Iteracja 2",
            "edges_detail": (
                "A→B: 0+2=2=2 ✗\nA→C: 0+4=4=4 ✗\nB→D: 2+3=5=5 ✗\nC→D: 4+5=9>5 ✗"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "5"},
            "relaxed": set(),
        },
        {
            "title": "Iteracja 3",
            "edges_detail": (
                "Brak zmian → stabilne!\n(wczesne zakończenie\n optymalizacja)"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "5"},
            "relaxed": set(),
        },
    ]

    for i, it in enumerate(iterations):
        # Graph subplot
        ax_g = fig.add_subplot(2, 4, i + 1)
        draw_full_graph(
            ax_g,
            title=it["title"],
            dist=it["dist"],
            current=None,
            visited=set() if i == 0 else {"A", "B", "C", "D"},
            relaxed_edges=it["relaxed"],
        )

        # Detail subplot below
        ax_d = fig.add_subplot(2, 4, i + 5)
        ax_d.axis("off")
        ax_d.text(
            0.5,
            0.5,
            it["edges_detail"],
            ha="center",
            va="center",
            fontsize=FS,
            family="monospace",
            bbox={"boxstyle": "round,pad=0.4", "facecolor": GRAY4, "edgecolor": GRAY3},
        )

    # Negative cycle check note
    neg_cycle_msg = (
        "Po 3 iteracjach: sprawdz raz jeszcze"
        " — nic sie nie zmienia"
        " → BRAK cyklu ujemnego → wynik poprawny"
    )
    fig.text(
        0.5,
        0.01,
        neg_cycle_msg,
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_GREEN,
            "edgecolor": LN,
        },
    )

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(
        str(Path(OUTPUT_DIR) / "bellman_ford_traversal.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("bellman_ford_traversal.png")


# ============================================================
# 4. A* traversal
# ============================================================
def draw_astar_traversal() -> None:
    """Draw step-by-step A* on the shared graph with heuristics."""
    # Heuristic values (straight-line distance to D)
    h_vals = {"A": 4, "B": 2, "C": 3, "D": 0}

    fig = plt.figure(figsize=(14, 7.5))
    fig.suptitle(
        "A* — przejście grafu krok po kroku (cel = D)\n"
        "f(n) = g(n) + h(n), heurystyka h"
        " = oszacowana odległość do D",
        fontsize=FS_TITLE,
        fontweight="bold",
        y=0.99,
    )

    steps = [
        {
            "title": "Krok 0: Inicjalizacja\nh(A)=4, h(B)=2, h(C)=3, h(D)=0",
            "detail": (
                "g(A)=0, f(A)=0+4=4\npq = [(4, A)]\nh = oszacowanie\n  odl. do celu D"
            ),
            "dist": {"A": "0"},
            "f_vals": {"A": "f=4"},
            "current": "A",
            "visited": set(),
            "relaxed": set(),
        },
        {
            "title": "Krok 1: pop A (f=4)\nA→B: g=2, f=2+2=4\nA→C: g=4, f=4+3=7",
            "detail": (
                "Relaksacja:\n"
                " A→B: g=0+2=2\n"
                "  f=2+h(B)=2+2=4\n"
                " A→C: g=0+4=4\n"
                "  f=4+h(C)=4+3=7\n"
                "pq = [(4,B), (7,C)]"
            ),
            "dist": {"A": "0", "B": "2", "C": "4"},
            "current": "A",
            "visited": {"A"},
            "relaxed": {("A", "B"), ("A", "C")},
        },
        {
            "title": "Krok 2: pop B (f=4) — min!\nB→D: g=5, f=5+0=5",
            "detail": (
                "B ma f=4 < C(f=7)\n"
                "→ A* kieruje się\n"
                "  W STRONĘ celu!\n"
                "Relaksacja:\n"
                " B→D: g=2+3=5\n"
                "  f=5+h(D)=5+0=5\n"
                "pq = [(5,D), (7,C)]"
            ),
            "dist": {"A": "0", "B": "2", "C": "4", "D": "5"},
            "current": "B",
            "visited": {"A", "B"},
            "relaxed": {("B", "D")},
        },
        {
            "title": "Krok 3: pop D (f=5)\nu == goal → STOP!",
            "detail": (
                "D to CEL → KONIEC!\n"
                "Nie przetwarzamy C\n"
                "  (f(C)=7 > f(D)=5)\n\n"
                "Ścieżka: A→B→D\n"
                "Koszt: 5\n\n"
                "Dijkstra odwi-\n"
                "edziłby też C!"
            ),
            "dist": {"A": "0", "B": "2", "D": "5"},
            "current": "D",
            "visited": {"A", "B", "D"},
            "relaxed": set(),
        },
    ]

    for i, step in enumerate(steps):
        # Graph
        ax_g = fig.add_subplot(2, 4, i + 1)
        draw_full_graph(
            ax_g,
            title=step["title"],
            dist=step["dist"],
            current=step["current"],
            visited=step["visited"],
            relaxed_edges=step["relaxed"],
        )

        # Add h values as small labels
        for node_name, pos in NODE_POS.items():
            ax_g.text(
                pos[0] + 0.35,
                pos[1] + 0.35,
                f"h={h_vals[node_name]}",
                ha="center",
                va="center",
                fontsize=5.5,
                color="#1565C0",
                fontweight="bold",
                zorder=7,
                bbox={
                    "boxstyle": "round,pad=0.1",
                    "facecolor": LIGHT_BLUE,
                    "edgecolor": "#1565C0",
                    "alpha": 0.9,
                    "lw": 0.5,
                },
            )

        # Detail
        ax_d = fig.add_subplot(2, 4, i + 5)
        ax_d.axis("off")
        ax_d.text(
            0.5,
            0.5,
            step["detail"],
            ha="center",
            va="center",
            fontsize=FS,
            family="monospace",
            bbox={"boxstyle": "round,pad=0.4", "facecolor": GRAY4, "edgecolor": GRAY3},
        )

    # Comparison note
    fig.text(
        0.5,
        0.01,
        "A* odwiedził 3 wierzchołki (A, B, D)"
        " — POMINĄŁ C!\n"
        "Dijkstra odwiedziłby wszystkie 4."
        " Heurystyka h kieruje przeszukiwanie"
        " w stronę celu.",
        ha="center",
        fontsize=FS,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": LIGHT_BLUE,
            "edgecolor": "#1565C0",
        },
    )

    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    plt.savefig(
        str(Path(OUTPUT_DIR) / "astar_traversal.png"),
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BG,
    )
    plt.close()
    _logger.info("astar_traversal.png")


# ============================================================
# Main
# ============================================================

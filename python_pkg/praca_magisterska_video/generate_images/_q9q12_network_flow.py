"""PYTANIE 12 flow diagrams: Ford-Fulkerson, Hungarian, min-cost flow."""

from __future__ import annotations

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

from python_pkg.praca_magisterska_video.generate_images._q9q12_common import (
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY3,
    GRAY4,
    LIGHT_GREEN,
    LIGHT_RED,
    LIGHT_YELLOW,
    LN,
    draw_network_edge,
    draw_network_node,
    save_fig,
)


def gen_ford_fulkerson() -> None:
    """Ford-Fulkerson max flow step-by-step."""
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    fig.suptitle(
        "Ford-Fulkerson — Maksymalny przepływ (krok po kroku)",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    pos = {"s": (0.5, 1.5), "A": (2.5, 2.5), "B": (2.5, 0.5), "t": (4.5, 1.5)}

    steps = [
        {
            "title": "Krok 0: Sieć wejściowa\n(przepustowości)",
            "edges": [
                ("s", "A", "10"),
                ("s", "B", "8"),
                ("A", "t", "6"),
                ("B", "t", "10"),
                ("B", "A", "2"),
            ],
            "flows": {},
            "path": [],
            "note": "Szukamy ścieżki s→...→t",
        },
        {
            "title": "Krok 1: Ścieżka s→A→t\nPrzepływ: +6 (min(10,6))",
            "edges": [
                ("s", "A", "4/10"),
                ("s", "B", "0/8"),
                ("A", "t", "6/6"),
                ("B", "t", "0/10"),
                ("B", "A", "0/2"),
            ],
            "flows": {},
            "path": [("s", "A"), ("A", "t")],
            "note": "Łączny przepływ: 6",
        },
        {
            "title": "Krok 2: Ścieżka s→B→t\nPrzepływ: +8 (min(8,10))",
            "edges": [
                ("s", "A", "4/10"),
                ("s", "B", "8/8"),
                ("A", "t", "6/6"),
                ("B", "t", "8/10"),
                ("B", "A", "0/2"),
            ],
            "flows": {},
            "path": [("s", "B"), ("B", "t")],
            "note": "Łączny przepływ: 14",
        },
        {
            "title": "Krok 3: Brak ścieżki powiększającej\nMAX FLOW = 14",
            "edges": [
                ("s", "A", "4/10"),
                ("s", "B", "8/8"),
                ("A", "t", "6/6"),
                ("B", "t", "8/10"),
                ("B", "A", "0/2"),
            ],
            "flows": {},
            "path": [],
            "note": "Min-cut: {s,A,B}|{t}\nA→t(6)+B→t(10)=16? Nie!\ns→B(8)+A→t(6)=14 ✓",
        },
    ]

    for _idx, (ax, step) in enumerate(zip(axes.flat, steps, strict=False)):
        ax.set_xlim(-0.3, 5.3)
        ax.set_ylim(-0.3, 3.3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(step["title"], fontsize=FS, fontweight="bold", pad=5)

        path_set = set(step["path"])

        for e in step["edges"]:
            u, v, label = e
            is_path = (u, v) in path_set
            c = "#C62828" if is_path else LN
            w = 2.5 if is_path else 1.5
            draw_network_edge(ax, pos[u], pos[v], label=label, color=c, lw=w)

        for name, p in pos.items():
            if name == "s":
                c = LIGHT_GREEN
            elif name == "t":
                c = LIGHT_RED
            else:
                c = "white"
            draw_network_node(ax, name, p, color=c)

        ax.text(
            2.5,
            -0.15,
            step["note"],
            fontsize=FS_SMALL,
            ha="center",
            va="center",
            style="italic",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": GRAY4, "edgecolor": GRAY3},
        )

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, "ford_fulkerson_example.png")


def gen_hungarian() -> None:
    """Hungarian algorithm step-by-step."""
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    fig.suptitle(
        "Algorytm węgierski — Problem przydziału (krok po kroku)",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    matrices = [
        {
            "title": "Macierz kosztów (wejściowa)",
            "data": [[8, 4, 7], [5, 2, 3], [9, 4, 8]],
            "highlight": [],
            "note": "Minimalizuj łączny koszt przydziału",
        },
        {
            "title": "Krok 1: Redukcja wierszy\n(odejmij min z wiersza)",
            "data": [[4, 0, 3], [3, 0, 1], [5, 0, 4]],
            "highlight": [(0, 1), (1, 1), (2, 1)],
            "note": "min: A=4, B=2, C=4",
        },
        {
            "title": "Krok 2: Redukcja kolumn\n(odejmij min z kolumny)",
            "data": [[1, 0, 2], [0, 0, 0], [2, 0, 3]],
            "highlight": [(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)],
            "note": "min: Z1=3, Z2=0, Z3=1",
        },
        {
            "title": "Krok 3: Optymalne przypisanie\nA→Z2(4), B→Z1(5), C=?",
            "data": [[0, 0, 1], [0, 1, 0], [1, 0, 2]],
            "highlight": [(0, 1), (1, 0), (2, 1)],
            "note": "Optymalne: A→Z1(8) + B→Z3(3) + C→Z2(4) = 15",
        },
    ]

    rows = ["A", "B", "C"]
    cols = ["Z1", "Z2", "Z3"]

    for ax, m in zip(axes.flat, matrices, strict=False):
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-1, 4.5)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(m["title"], fontsize=FS, fontweight="bold", pad=5)

        # Column headers
        for j, col in enumerate(cols):
            ax.text(
                j + 1.5,
                3.8,
                col,
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
            )

        # Row headers and data
        for i, row in enumerate(rows):
            y = 2.8 - i
            ax.text(
                0.3, y, row, ha="center", va="center", fontsize=9, fontweight="bold"
            )
            for j in range(3):
                val = m["data"][i][j]
                is_zero = val == 0
                is_hl = (i, j) in m["highlight"]
                fc = (
                    LIGHT_GREEN if is_hl else ("white" if not is_zero else LIGHT_YELLOW)
                )
                rect = FancyBboxPatch(
                    (j + 1.0, y - 0.35),
                    1.0,
                    0.7,
                    boxstyle="round,pad=0.05",
                    lw=1.2,
                    edgecolor=LN if not is_hl else "#1B5E20",
                    facecolor=fc,
                )
                ax.add_patch(rect)
                ax.text(
                    j + 1.5,
                    y,
                    str(val),
                    ha="center",
                    va="center",
                    fontsize=10,
                    fontweight="bold" if is_hl else "normal",
                )

        ax.text(
            2.0,
            -0.6,
            m["note"],
            fontsize=FS_SMALL,
            ha="center",
            va="center",
            style="italic",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": GRAY4, "edgecolor": GRAY3},
        )

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, "hungarian_example.png")


def gen_min_cost_flow() -> None:
    """Min-cost flow example."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle(
        "Minimalny koszt przepływu — transport 10 ton",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    pos = {"s": (0.5, 1.5), "A": (2.5, 2.5), "B": (2.5, 0.5), "t": (4.5, 1.5)}

    # Left: network with capacities and costs
    ax = axes[0]
    ax.set_xlim(-0.3, 5.3)
    ax.set_ylim(-0.3, 3.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Sieć (przepustowość, koszt/t)", fontsize=FS, fontweight="bold")

    edges_info = [
        ("s", "A", "(8, 2zł)"),
        ("s", "B", "(5, 4zł)"),
        ("A", "t", "(6, 3zł)"),
        ("B", "t", "(5, 1zł)"),
    ]
    for u, v, label in edges_info:
        draw_network_edge(ax, pos[u], pos[v], label=label, r=0.33)

    for name, p in pos.items():
        c = LIGHT_GREEN if name == "s" else (LIGHT_RED if name == "t" else "white")
        draw_network_node(ax, name, p, color=c)

    # Right: optimal flow
    ax = axes[1]
    ax.set_xlim(-0.3, 5.3)
    ax.set_ylim(-0.3, 3.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Optymalny przepływ (koszt = 50 zł)", fontsize=FS, fontweight="bold")

    opt_edges = [
        ("s", "A", "5/8", "#1B5E20"),
        ("s", "B", "5/5", "#C62828"),
        ("A", "t", "5/6", "#1B5E20"),
        ("B", "t", "5/5", "#C62828"),
    ]
    for u, v, label, color in opt_edges:
        draw_network_edge(ax, pos[u], pos[v], label=label, color=color, lw=2.0, r=0.33)

    for name, p in pos.items():
        c = LIGHT_GREEN if name == "s" else (LIGHT_RED if name == "t" else "white")
        draw_network_node(ax, name, p, color=c)

    ax.text(
        2.5,
        -0.15,
        "5tx(2+3)=25zł + 5tx(4+1)=25zł = 50zł",
        fontsize=FS,
        ha="center",
        style="italic",
        bbox={"boxstyle": "round,pad=0.15", "facecolor": GRAY4, "edgecolor": GRAY3},
    )

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save_fig(fig, "min_cost_flow_example.png")

"""PYTANIE 12 graph diagrams: CPM, Kruskal, TSP."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from python_pkg.praca_magisterska_video.generate_images._q9q12_common import (
    _CENTER_Y,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY3,
    GRAY4,
    LIGHT_BLUE,
    LIGHT_GREEN,
    LIGHT_RED,
    LN,
    draw_network_edge,
    draw_network_node,
    save_fig,
)


def gen_cpm() -> None:
    """CPM critical path diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-0.5, 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "CPM — Ścieżka krytyczna projektu IT",
        fontsize=FS_TITLE,
        fontweight="bold",
        pad=10,
    )

    # Task positions: (x, y)
    tasks = {
        "START": (0.5, 2.5),
        "A\n3 tyg": (2.5, 2.5),
        "B\n4 tyg": (5.0, 3.8),
        "C\n5 tyg": (5.0, 1.2),
        "D\n6 tyg": (7.5, 3.8),
        "E\n2 tyg": (9.5, 2.5),
        "F\n1 tyg": (11.5, 2.5),
    }

    # Critical path: START→A→B→D→E→F
    critical = {"START", "A\n3 tyg", "B\n4 tyg", "D\n6 tyg", "E\n2 tyg", "F\n1 tyg"}
    critical_edges = {
        ("START", "A\n3 tyg"),
        ("A\n3 tyg", "B\n4 tyg"),
        ("B\n4 tyg", "D\n6 tyg"),
        ("D\n6 tyg", "E\n2 tyg"),
        ("E\n2 tyg", "F\n1 tyg"),
    }

    edges = [
        ("START", "A\n3 tyg"),
        ("A\n3 tyg", "B\n4 tyg"),
        ("A\n3 tyg", "C\n5 tyg"),
        ("B\n4 tyg", "D\n6 tyg"),
        ("C\n5 tyg", "E\n2 tyg"),
        ("D\n6 tyg", "E\n2 tyg"),
        ("E\n2 tyg", "F\n1 tyg"),
    ]

    # Draw edges
    for u, v in edges:
        is_crit = (u, v) in critical_edges
        c = "#C62828" if is_crit else GRAY3
        w = 2.5 if is_crit else 1.2
        draw_network_edge(ax, tasks[u], tasks[v], color=c, lw=w, r=0.5)

    # Draw nodes
    for name, p in tasks.items():
        is_crit = name in critical
        c = LIGHT_RED if is_crit else LIGHT_BLUE
        r = 0.45
        circle = plt.Circle(
            p,
            r,
            fill=True,
            facecolor=c,
            edgecolor="#C62828" if is_crit else LN,
            linewidth=2.0 if is_crit else 1.2,
            zorder=5,
        )
        ax.add_patch(circle)
        ax.text(
            p[0],
            p[1],
            name,
            ha="center",
            va="center",
            fontsize=7 if "\n" in name else 8,
            fontweight="bold",
            zorder=6,
        )

    # ES/EF labels
    es_ef = [
        ("A\n3 tyg", "ES=0, EF=3"),
        ("B\n4 tyg", "ES=3, EF=7"),
        ("C\n5 tyg", "ES=3, EF=8\nzapas=5"),
        ("D\n6 tyg", "ES=7, EF=13"),
        ("E\n2 tyg", "ES=13, EF=15"),
        ("F\n1 tyg", "ES=15, EF=16"),
    ]
    for name, label in es_ef:
        x, y = tasks[name]
        offset_y = 0.7 if y > _CENTER_Y else -0.7
        ax.text(
            x,
            y + offset_y,
            label,
            ha="center",
            va="center",
            fontsize=FS_SMALL,
            bbox={
                "boxstyle": "round,pad=0.1",
                "facecolor": "white",
                "edgecolor": GRAY3,
                "alpha": 0.95,
            },
        )

    # Legend
    ax.text(
        0.5,
        -0.2,
        "Ścieżka krytyczna: A→B→D→E→F (16 tyg)",
        fontsize=9,
        fontweight="bold",
        color="#C62828",
    )
    ax.text(
        0.5,
        -0.6,
        "C ma 5 tyg zapasu — może się opóźnić bez wpływu na projekt",
        fontsize=FS,
        style="italic",
    )

    save_fig(fig, "cpm_example.png")


def gen_kruskal() -> None:
    """Kruskal MST construction step-by-step."""
    fig, axes = plt.subplots(2, 2, figsize=(9, 8))
    fig.suptitle(
        "Kruskal — budowa MST krok po kroku", fontsize=FS_TITLE, fontweight="bold"
    )

    pos = {"A": (0.5, 2.5), "B": (3.0, 2.5), "C": (3.0, 0.5), "D": (0.5, 0.5)}

    all_edges = [
        ("C", "D", 1),
        ("A", "C", 2),
        ("A", "B", 4),
        ("B", "C", 6),
        ("B", "D", 7),
        ("A", "D", 8),
    ]

    steps = [
        {
            "title": "Graf wejściowy\n(6 krawędzi)",
            "mst": [],
            "consider": None,
            "note": "Posortowane: CD(1), AC(2), AB(4), BC(6), BD(7), AD(8)",
        },
        {
            "title": "Krok 1: Dodaj C-D (waga 1)\nNajlżejsza krawędź",
            "mst": [("C", "D", 1)],
            "consider": ("C", "D"),
            "note": "MST = {C-D}, koszt = 1",
        },
        {
            "title": "Krok 2: Dodaj A-C (waga 2)\nA nie w {C,D}",
            "mst": [("C", "D", 1), ("A", "C", 2)],
            "consider": ("A", "C"),
            "note": "MST = {C-D, A-C}, koszt = 3",
        },
        {
            "title": "Krok 3: Dodaj A-B (waga 4)\nB nie w {A,C,D} → KONIEC",
            "mst": [("C", "D", 1), ("A", "C", 2), ("A", "B", 4)],
            "consider": ("A", "B"),
            "note": "MST = {C-D, A-C, A-B}, koszt = 7 ✓",
        },
    ]

    for ax, step in zip(axes.flat, steps, strict=False):
        ax.set_xlim(-0.5, 4.0)
        ax.set_ylim(-0.5, 3.5)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(step["title"], fontsize=FS, fontweight="bold", pad=5)

        mst_set = {(u, v) for u, v, _ in step["mst"]}

        for u, v, w in all_edges:
            in_mst = (u, v) in mst_set or (v, u) in mst_set
            is_cur = step["consider"] and (
                (u, v) == step["consider"] or (v, u) == step["consider"]
            )
            if is_cur:
                c, lw = "#C62828", 3.0
            elif in_mst:
                c, lw = "#1B5E20", 2.5
            else:
                c, lw = GRAY3, 1.0
            draw_network_edge(
                ax,
                pos[u],
                pos[v],
                label=str(w),
                color=c,
                lw=lw,
                directed=False,
                label_bg=LIGHT_GREEN if in_mst else "white",
            )

        for name, p in pos.items():
            # Check if in current MST component
            in_mst = any(name in (u, v) for u, v, _ in step["mst"])
            c = LIGHT_GREEN if in_mst else "white"
            draw_network_node(ax, name, p, color=c, r=0.3)

        ax.text(
            1.75,
            -0.3,
            step["note"],
            fontsize=FS_SMALL,
            ha="center",
            va="center",
            style="italic",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": GRAY4, "edgecolor": GRAY3},
        )

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_fig(fig, "kruskal_example.png")


def gen_tsp() -> None:
    """TSP nearest neighbor heuristic."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.suptitle(
        "TSP — heurystyka Nearest Neighbor (5 miast)",
        fontsize=FS_TITLE,
        fontweight="bold",
    )

    pos = {
        "A": (0.5, 3.0),
        "B": (2.0, 4.0),
        "C": (4.0, 3.5),
        "D": (3.5, 1.0),
        "E": (1.5, 1.5),
    }

    dist = {
        ("A", "B"): 20,
        ("A", "C"): 42,
        ("A", "D"): 35,
        ("A", "E"): 12,
        ("B", "C"): 30,
        ("B", "D"): 34,
        ("B", "E"): 10,
        ("C", "D"): 12,
        ("C", "E"): 40,
        ("D", "E"): 25,
    }

    # Left: full graph with all distances
    ax = axes[0]
    ax.set_xlim(-0.5, 5.0)
    ax.set_ylim(0, 5.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Graf pełny (odległości)", fontsize=FS, fontweight="bold")

    for (u, v), d in dist.items():
        draw_network_edge(
            ax, pos[u], pos[v], label=str(d), color=GRAY3, lw=0.8, directed=False, r=0.3
        )

    for name, p in pos.items():
        draw_network_node(ax, name, p, color=LIGHT_BLUE, r=0.3)

    # Right: NN solution
    ax = axes[1]
    ax.set_xlim(-0.5, 5.0)
    ax.set_ylim(0, 5.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Nearest Neighbor (start A)\nTrasa: A→E→B→C→D→A = 99",
        fontsize=FS,
        fontweight="bold",
    )

    nn_path = [
        ("A", "E", 12),
        ("E", "B", 10),
        ("B", "C", 30),
        ("C", "D", 12),
        ("D", "A", 35),
    ]
    colors = ["#C62828", "#1B5E20", "#1565C0", "#E65100", "#4A148C"]

    for i, (u, v, d) in enumerate(nn_path):
        draw_network_edge(
            ax,
            pos[u],
            pos[v],
            label=f"{d}",
            color=colors[i],
            lw=2.0,
            directed=True,
            r=0.3,
        )
        # Step number
        mx = (pos[u][0] + pos[v][0]) / 2
        my = (pos[u][1] + pos[v][1]) / 2
        dx = pos[v][0] - pos[u][0]
        dy = pos[v][1] - pos[u][1]
        length = np.sqrt(dx**2 + dy**2)
        ox = dy / length * 0.45
        oy = -dx / length * 0.45
        ax.text(
            mx + ox,
            my + oy,
            f"#{i + 1}",
            fontsize=FS_SMALL,
            ha="center",
            color=colors[i],
            fontweight="bold",
        )

    for name, p in pos.items():
        c = LIGHT_GREEN if name == "A" else LIGHT_BLUE
        draw_network_node(ax, name, p, color=c, r=0.3)

    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save_fig(fig, "tsp_nearest_neighbor.png")

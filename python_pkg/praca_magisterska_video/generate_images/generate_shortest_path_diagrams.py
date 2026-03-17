#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 2: Shortest path algorithms.

  1. Graph structure -- the shared example graph (A,B,C,D)
  2. Dijkstra traversal -- step-by-step on that graph
  3. Bellman-Ford traversal -- step-by-step
  4. A* traversal -- step-by-step with heuristics.

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_logger = logging.getLogger(__name__)

DPI = 300
BG = "white"
LN = "black"
FS = 8
FS_TITLE = 11
FS_EDGE = 9
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
LIGHT_GREEN = "#D5E8D4"
LIGHT_BLUE = "#D6EAF8"
LIGHT_YELLOW = "#FFF9C4"

NODE_POS: dict[str, tuple[float, float]] = {
    "A": (1, 2),
    "B": (3.5, 3.2),
    "C": (1, 0),
    "D": (3.5, 0.8),
}
EDGES: list[tuple[str, str, int]] = [
    ("A", "B", 2),
    ("A", "C", 4),
    ("B", "D", 3),
    ("C", "D", 5),
]


def draw_graph_node(
    ax: Axes,
    name: str,
    pos: tuple[float, float],
    *,
    color: str = "white",
    current: bool = False,
    visited: bool = False,
    dist_label: str | None = None,
    fontsize: int = 12,
) -> None:
    """Draw a graph node (circle with label).

    Args:
        ax: Matplotlib axes to draw on.
        name: Node label text.
        pos: (x, y) position of the node center.
        color: Fill color when not current/visited.
        current: Whether this node is being processed.
        visited: Whether this node has been visited.
        dist_label: Optional distance label below node.
        fontsize: Font size for the node label.
    """
    x, y = pos
    radius = 0.35
    lw = 2.5 if current else 1.5
    ec = "#D32F2F" if current else LN
    fc = LIGHT_GREEN if visited else color
    if current:
        fc = LIGHT_YELLOW

    circle = plt.Circle(
        (x, y),
        radius,
        fill=True,
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        zorder=5,
    )
    ax.add_patch(circle)
    ax.text(
        x,
        y,
        name,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        zorder=6,
    )

    if dist_label is not None:
        ax.text(
            x,
            y - 0.55,
            f"d={dist_label}",
            ha="center",
            va="center",
            fontsize=FS,
            zorder=6,
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": "white",
                "edgecolor": GRAY3,
                "alpha": 0.95,
            },
        )


def draw_graph_edge(
    ax: Axes,
    pos1: tuple[float, float],
    pos2: tuple[float, float],
    weight: int,
    *,
    highlighted: bool = False,
    relaxed: bool = False,
) -> None:
    """Draw an edge between two nodes with weight label.

    Args:
        ax: Matplotlib axes to draw on.
        pos1: Start node position.
        pos2: End node position.
        weight: Edge weight value.
        highlighted: Whether edge is highlighted.
        relaxed: Whether edge was just relaxed.
    """
    x1, y1 = pos1
    x2, y2 = pos2

    # Shorten line to not overlap node circles
    dx, dy = x2 - x1, y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    node_radius = 0.38
    sx = x1 + node_radius * dx / length
    sy = y1 + node_radius * dy / length
    ex = x2 - node_radius * dx / length
    ey = y2 - node_radius * dy / length

    color = "#D32F2F" if relaxed else ("#1565C0" if highlighted else GRAY3)
    lw = 2.5 if (highlighted or relaxed) else 1.5

    ax.plot(
        [sx, ex],
        [sy, ey],
        color=color,
        linewidth=lw,
        linestyle="-",
        zorder=2,
    )

    # Weight label
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    # Offset perpendicular to edge
    perp_x = -dy / length * 0.2
    perp_y = dx / length * 0.2

    ax.text(
        mx + perp_x,
        my + perp_y,
        str(weight),
        ha="center",
        va="center",
        fontsize=FS_EDGE,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.15",
            "facecolor": "white",
            "edgecolor": (GRAY3 if not highlighted else color),
            "alpha": 0.95,
        },
        zorder=4,
    )


def draw_full_graph(
    ax: Axes,
    *,
    title: str = "",
    dist: dict[str, str] | None = None,
    current: str | None = None,
    visited: set[str] | None = None,
    highlighted_edges: set[tuple[str, str]] | None = None,
    relaxed_edges: set[tuple[str, str]] | None = None,
) -> None:
    """Draw the complete graph with optional highlighting.

    Args:
        ax: Matplotlib axes to draw on.
        title: Subplot title.
        dist: Distance labels per node.
        current: Currently processed node name.
        visited: Set of visited node names.
        highlighted_edges: Edges to highlight.
        relaxed_edges: Edges that were just relaxed.
    """
    if visited is None:
        visited = set()
    if highlighted_edges is None:
        highlighted_edges = set()
    if relaxed_edges is None:
        relaxed_edges = set()
    if dist is None:
        dist = {}

    ax.set_xlim(-0.2, 4.7)
    ax.set_ylim(-0.8, 4.2)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=FS, fontweight="bold", pad=5)

    # Draw edges
    for u, v, w in EDGES:
        hl = (u, v) in highlighted_edges or (v, u) in highlighted_edges
        rl = (u, v) in relaxed_edges or (v, u) in relaxed_edges
        draw_graph_edge(
            ax,
            NODE_POS[u],
            NODE_POS[v],
            w,
            highlighted=hl,
            relaxed=rl,
        )

    # Draw nodes
    for node_name, pos in NODE_POS.items():
        is_current = node_name == current
        is_visited = node_name in visited
        d_label = dist.get(node_name)
        draw_graph_node(
            ax,
            node_name,
            pos,
            current=is_current,
            visited=is_visited,
            dist_label=d_label,
        )


# ============================================================
# 1. Graph structure diagram


if __name__ == "__main__":
    from python_pkg.praca_magisterska_video.generate_images._shortest_path_traversals import (
        draw_astar_traversal,
        draw_bellman_ford_traversal,
        draw_dijkstra_traversal,
        draw_graph_structure,
    )

    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating shortest path diagrams...")
    draw_graph_structure()
    draw_dijkstra_traversal()
    draw_bellman_ford_traversal()
    draw_astar_traversal()
    _logger.info("All shortest path diagrams saved to %s/", OUTPUT_DIR)

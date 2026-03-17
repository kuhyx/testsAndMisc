#!/usr/bin/env python3
"""Generate Bellman-Ford negative-weights & negative-cycle diagram.

Diagram for PYTANIE 2. Two-part figure:
  Part 1: Graph with negative edge, Dijkstra WRONG vs Bellman-Ford CORRECT
  Part 2: Negative cycle detection (add C->B(-3))

A4-compatible, monochrome-friendly, 300 DPI.
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
FS_TITLE = 10
FS_SMALL = 6.5
FS_EDGE = 9
OUTPUT_DIR = str(Path(__file__).resolve().parent / "img")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

GRAY1 = "#E8E8E8"
GRAY2 = "#D0D0D0"
GRAY3 = "#B8B8B8"
GRAY4 = "#F5F5F5"
LIGHT_GREEN = "#D5E8D4"
LIGHT_RED = "#F8D7DA"
LIGHT_YELLOW = "#FFF9C4"

# Graph layout for negative-weight example:
# S->A(2), A->C(3), S->B(5), B->A(-4)
NEG_POS: dict[str, tuple[float, float]] = {
    "S": (0.8, 2),
    "A": (3.3, 3.2),
    "B": (3.3, 0.8),
    "C": (5.8, 2),
}
NEG_EDGES: list[tuple[str, str, int]] = [
    ("S", "A", 2),
    ("A", "C", 3),
    ("S", "B", 5),
    ("B", "A", -4),
]


def draw_node(
    ax: Axes,
    name: str,
    pos: tuple[float, float],
    *,
    color: str = "white",
    current: bool = False,
    visited: bool = False,
    dist_label: str | None = None,
    fontsize: int = 12,
    error: bool = False,
) -> None:
    """Draw a graph node with optional distance label."""
    x, y = pos
    r = 0.35
    lw = 2.5 if current else 1.5
    ec = "#D32F2F" if current else ("#D32F2F" if error else LN)
    fc = LIGHT_YELLOW if current else (LIGHT_GREEN if visited else color)
    if error:
        fc = LIGHT_RED

    circle = plt.Circle(
        (x, y),
        r,
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
        bbox_ec = "#D32F2F" if error else GRAY3
        bbox_fc = LIGHT_RED if error else "white"
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
                "facecolor": bbox_fc,
                "edgecolor": bbox_ec,
                "alpha": 0.95,
            },
        )


def _choose_edge_style(
    *,
    negative: bool,
    relaxed: bool,
    highlighted: bool,
    cycle_edge: bool,
) -> tuple[str, float, str]:
    """Return (color, lw, linestyle) for an edge."""
    if cycle_edge:
        return "#D32F2F", 2.5, "--"
    if negative or relaxed:
        return "#D32F2F", 2.5, "-"
    if highlighted:
        return "#1565C0", 2.0, "-"
    return GRAY3, 1.5, "-"


def draw_edge(
    ax: Axes,
    pos1: tuple[float, float],
    pos2: tuple[float, float],
    weight: int,
    *,
    highlighted: bool = False,
    relaxed: bool = False,
    negative: bool = False,
    cycle_edge: bool = False,
    offset: float = 0.0,
) -> None:
    """Draw a directed edge between two nodes with a weight label."""
    x1, y1 = pos1
    x2, y2 = pos2

    dx, dy = x2 - x1, y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    r = 0.38
    sx = x1 + r * dx / length
    sy = y1 + r * dy / length
    ex = x2 - r * dx / length
    ey = y2 - r * dy / length

    # Offset perpendicular for parallel edges
    if offset != 0:
        perp_x = -dy / length * offset
        perp_y = dx / length * offset
        sx += perp_x
        sy += perp_y
        ex += perp_x
        ey += perp_y

    color, lw, ls = _choose_edge_style(
        negative=negative,
        relaxed=relaxed,
        highlighted=highlighted,
        cycle_edge=cycle_edge,
    )

    # Arrow
    ax.annotate(
        "",
        xy=(ex, ey),
        xytext=(sx, sy),
        arrowprops={
            "arrowstyle": "->",
            "color": color,
            "lw": lw,
            "linestyle": ls,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=2,
    )

    # Weight label
    mx = (sx + ex) / 2
    my = (sy + ey) / 2
    perp_x = -dy / length * 0.22
    perp_y = dx / length * 0.22
    if offset != 0:
        perp_x *= 0.5
        perp_y *= 0.5

    weight_str = str(weight)
    edge_fc = LIGHT_RED if negative or cycle_edge else "white"
    edge_ec = "#D32F2F" if negative or cycle_edge else GRAY3
    ax.text(
        mx + perp_x,
        my + perp_y,
        weight_str,
        ha="center",
        va="center",
        fontsize=FS_EDGE,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.15",
            "facecolor": edge_fc,
            "edgecolor": edge_ec,
            "alpha": 0.95,
        },
        zorder=4,
    )


def draw_neg_graph(
    ax: Axes,
    edges: list[tuple[str, str, int]],
    *,
    title: str = "",
    dist: dict[str, str] | None = None,
    current: str | None = None,
    visited: set[str] | None = None,
    relaxed_edges: set[tuple[str, str]] | None = None,
    error_nodes: set[str] | None = None,
    extra_edges: list[tuple[str, str, int]] | None = None,
    node_positions: dict[str, tuple[float, float]] | None = None,
) -> None:
    """Draw the negative-weight graph with annotations."""
    if visited is None:
        visited = set()
    if relaxed_edges is None:
        relaxed_edges = set()
    if dist is None:
        dist = {}
    if error_nodes is None:
        error_nodes = set()
    if node_positions is None:
        node_positions = NEG_POS

    ax.set_xlim(-0.5, 7.0)
    ax.set_ylim(-0.8, 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=FS, fontweight="bold", pad=5)

    all_edges = list(edges)
    if extra_edges:
        all_edges += extra_edges

    for u, v, w in all_edges:
        rl = (u, v) in relaxed_edges
        neg = w < 0
        cycle = bool(extra_edges and (u, v, w) in extra_edges)
        draw_edge(
            ax,
            node_positions[u],
            node_positions[v],
            w,
            relaxed=rl,
            negative=neg,
            cycle_edge=cycle,
            offset=0.0,
        )

    for name, pos in node_positions.items():
        is_current = name == current
        is_visited = name in visited
        d_label = dist.get(name)
        is_error = name in error_nodes
        draw_node(
            ax,
            name,
            pos,
            current=is_current,
            visited=is_visited,
            dist_label=d_label,
            error=is_error,
        )


if __name__ == "__main__":
    from python_pkg.praca_magisterska_video.generate_images._bf_negative_diagrams import (
        generate_bf_negative_cycle,
        generate_bf_negative_weights,
    )

    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating B-F negative diagrams...")
    generate_bf_negative_weights()
    generate_bf_negative_cycle()
    _logger.info("All B-F negative diagrams saved to %s/", OUTPUT_DIR)

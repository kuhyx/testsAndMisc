"""Tests for shortest path diagram generators."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest


@pytest.fixture(autouse=True)
def _patch_savefig(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent matplotlib from writing files to disk."""
    monkeypatch.setattr(mpl.figure.Figure, "savefig", lambda *_a, **_kw: None)
    monkeypatch.setattr(plt, "savefig", lambda *_a, **_kw: None)


# =====================================================================
class TestShortestPathDiagrams:
    """Tests for generate_shortest_path_diagrams constants and helpers."""

    def test_constants_exist(self) -> None:
        from generate_shortest_path_diagrams import (
            BG,
            DPI,
            EDGES,
            FS,
            FS_EDGE,
            FS_TITLE,
            GRAY3,
            GRAY4,
            LIGHT_BLUE,
            LIGHT_GREEN,
            LIGHT_YELLOW,
            LN,
            NODE_POS,
        )

        assert DPI == 300
        assert BG == "white"
        assert LN == "black"
        assert FS == 8
        assert FS_TITLE == 11
        assert FS_EDGE == 9
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(LIGHT_GREEN, str)
        assert isinstance(LIGHT_BLUE, str)
        assert isinstance(LIGHT_YELLOW, str)
        assert isinstance(NODE_POS, dict)
        assert isinstance(EDGES, list)
        assert len(NODE_POS) == 4
        assert len(EDGES) == 4

    def test_draw_graph_node_default(self) -> None:
        from generate_shortest_path_diagrams import draw_graph_node

        _fig, ax = plt.subplots()
        draw_graph_node(ax, "A", (1.0, 2.0))
        plt.close()

    def test_draw_graph_node_current(self) -> None:
        from generate_shortest_path_diagrams import draw_graph_node

        _fig, ax = plt.subplots()
        draw_graph_node(ax, "B", (1.0, 2.0), current=True, dist_label="5")
        plt.close()

    def test_draw_graph_node_visited(self) -> None:
        from generate_shortest_path_diagrams import draw_graph_node

        _fig, ax = plt.subplots()
        draw_graph_node(ax, "C", (1.0, 2.0), visited=True, dist_label="∞")
        plt.close()

    def test_draw_graph_node_custom_color(self) -> None:
        from generate_shortest_path_diagrams import draw_graph_node

        _fig, ax = plt.subplots()
        draw_graph_node(ax, "D", (3.0, 1.0), color="#FF0000", fontsize=10)
        plt.close()

    def test_draw_graph_edge_default(self) -> None:
        from generate_shortest_path_diagrams import draw_graph_edge

        _fig, ax = plt.subplots()
        draw_graph_edge(ax, (0.0, 0.0), (3.0, 4.0), 5)
        plt.close()

    def test_draw_graph_edge_highlighted(self) -> None:
        from generate_shortest_path_diagrams import draw_graph_edge

        _fig, ax = plt.subplots()
        draw_graph_edge(ax, (0.0, 0.0), (3.0, 4.0), 5, highlighted=True)
        plt.close()

    def test_draw_graph_edge_relaxed(self) -> None:
        from generate_shortest_path_diagrams import draw_graph_edge

        _fig, ax = plt.subplots()
        draw_graph_edge(ax, (0.0, 0.0), (3.0, 4.0), 5, relaxed=True)
        plt.close()

    def test_draw_full_graph_defaults(self) -> None:
        from generate_shortest_path_diagrams import draw_full_graph

        _fig, ax = plt.subplots()
        draw_full_graph(ax)
        plt.close()

    def test_draw_full_graph_with_state(self) -> None:
        from generate_shortest_path_diagrams import draw_full_graph

        _fig, ax = plt.subplots()
        draw_full_graph(
            ax,
            title="Test",
            dist={"A": "0", "B": "2"},
            current="A",
            visited={"A"},
            highlighted_edges={("A", "B")},
            relaxed_edges={("B", "D")},
        )
        plt.close()

    def test_draw_full_graph_reverse_edge(self) -> None:
        from generate_shortest_path_diagrams import draw_full_graph

        _fig, ax = plt.subplots()
        draw_full_graph(
            ax,
            highlighted_edges={("B", "A")},
            relaxed_edges={("D", "B")},
        )
        plt.close()


# =====================================================================
# _shortest_path_traversals
# =====================================================================
class TestShortestPathTraversals:
    """Tests for _shortest_path_traversals diagram functions."""

    def test_draw_graph_structure(self) -> None:
        from _shortest_path_traversals import draw_graph_structure

        draw_graph_structure()

    def test_draw_dijkstra_traversal(self) -> None:
        from _shortest_path_traversals import draw_dijkstra_traversal

        draw_dijkstra_traversal()

    def test_draw_bellman_ford_traversal(self) -> None:
        from _shortest_path_traversals import draw_bellman_ford_traversal

        draw_bellman_ford_traversal()

    def test_draw_astar_traversal(self) -> None:
        from _shortest_path_traversals import draw_astar_traversal

        draw_astar_traversal()

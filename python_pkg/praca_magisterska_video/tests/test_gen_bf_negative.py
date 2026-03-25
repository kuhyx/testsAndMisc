"""Tests for Bellman-Ford negative diagram modules (GROUP 4).

Covers:
  - generate_bf_negative_diagram.py (helpers, draw_neg_graph)
  - _bf_negative_diagrams.py (generate_bf_negative_weights, _cycle)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

from python_pkg.praca_magisterska_video.generate_images import (
    generate_bf_negative_diagram as _bf_neg,
)
from python_pkg.praca_magisterska_video.generate_images._bf_negative_diagrams import (
    _add_annotation_box,
    generate_bf_negative_cycle,
    generate_bf_negative_weights,
)

pytestmark = pytest.mark.usefixtures("_no_savefig")

_MOD = "python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram"


# ── Helper functions ───────────────────────────────────────────────────


class TestBFHelpers:
    """Test draw_node, _choose_edge_style, draw_edge, draw_neg_graph."""

    def test_draw_node_default(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_node(ax, "S", (1, 1))
        plt.close(fig)

    def test_draw_node_current(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_node(ax, "A", (1, 1), current=True, dist_label="2")
        plt.close(fig)

    def test_draw_node_visited(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_node(ax, "B", (1, 1), visited=True, dist_label="5")
        plt.close(fig)

    def test_draw_node_error(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_node(ax, "C", (1, 1), error=True, dist_label="?")
        plt.close(fig)

    def test_draw_node_no_dist_label(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_node(ax, "X", (1, 1), visited=True)
        plt.close(fig)

    def test_choose_edge_style_cycle(self) -> None:
        _, lw, ls = _bf_neg._choose_edge_style(
            negative=False, relaxed=False, highlighted=False, cycle_edge=True
        )
        assert ls == "--"
        assert lw == 2.5

    def test_choose_edge_style_negative(self) -> None:
        _, lw, ls = _bf_neg._choose_edge_style(
            negative=True, relaxed=False, highlighted=False, cycle_edge=False
        )
        assert lw == 2.5
        assert ls == "-"

    def test_choose_edge_style_relaxed(self) -> None:
        _, lw, _ = _bf_neg._choose_edge_style(
            negative=False, relaxed=True, highlighted=False, cycle_edge=False
        )
        assert lw == 2.5

    def test_choose_edge_style_highlighted(self) -> None:
        color, _, ls = _bf_neg._choose_edge_style(
            negative=False, relaxed=False, highlighted=True, cycle_edge=False
        )
        assert ls == "-"
        assert color == "#1565C0"

    def test_choose_edge_style_default(self) -> None:
        color, lw, _ = _bf_neg._choose_edge_style(
            negative=False, relaxed=False, highlighted=False, cycle_edge=False
        )
        assert color == _bf_neg.GRAY3
        assert lw == 1.5

    def test_draw_edge_no_offset(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_edge(ax, (0, 0), (2, 2), 3)
        plt.close(fig)

    def test_draw_edge_with_offset(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_edge(ax, (0, 0), (2, 2), -3, negative=True, offset=0.3)
        plt.close(fig)

    def test_draw_edge_highlighted(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_edge(ax, (0, 0), (2, 2), 5, highlighted=True)
        plt.close(fig)

    def test_draw_edge_cycle(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        _bf_neg.draw_edge(ax, (0, 0), (2, 2), -2, cycle_edge=True)
        plt.close(fig)


class TestDrawNegGraph:
    """Test draw_neg_graph with various argument combos."""

    def test_minimal(self) -> None:
        """All-defaults: visited, relaxed, dist, error_nodes all None."""
        fig, ax = plt.subplots()
        _bf_neg.draw_neg_graph(ax, _bf_neg.NEG_EDGES)
        plt.close(fig)

    def test_with_title(self) -> None:
        fig, ax = plt.subplots()
        _bf_neg.draw_neg_graph(ax, _bf_neg.NEG_EDGES, title="Test")
        plt.close(fig)

    def test_with_all_options(self) -> None:
        fig, ax = plt.subplots()
        _bf_neg.draw_neg_graph(
            ax,
            _bf_neg.NEG_EDGES,
            title="Full",
            dist={"S": "0", "A": "1", "B": "5", "C": "4"},
            current="S",
            visited={"S", "A"},
            relaxed_edges={("S", "A")},
            error_nodes={"C"},
            extra_edges=[("C", "B", -3)],
            node_positions=_bf_neg.NEG_POS,
        )
        plt.close(fig)

    def test_explicit_node_positions(self) -> None:
        """Cover node_positions is not None branch."""
        pos = {"X": (1.0, 1.0), "Y": (3.0, 1.0)}
        fig, ax = plt.subplots()
        _bf_neg.draw_neg_graph(
            ax,
            [("X", "Y", 2)],
            node_positions=pos,
            dist={"X": "0", "Y": "2"},
            visited={"X", "Y"},
        )
        plt.close(fig)


# ── _bf_negative_diagrams functions ────────────────────────────────────


class TestBFDiagramFunctions:
    """Test the main diagram generation functions."""

    def test_generate_bf_negative_weights(self) -> None:
        generate_bf_negative_weights()

    def test_generate_bf_negative_cycle(self) -> None:
        generate_bf_negative_cycle()

    def test_add_annotation_box(self) -> None:
        fig, ax = plt.subplots()
        _add_annotation_box(ax, 1, 1, "test", color="red", bg_color="white")
        plt.close(fig)


class TestBFModuleConstants:
    """Verify module-level constants."""

    def test_constants(self) -> None:
        assert _bf_neg.DPI == 300
        assert _bf_neg.BG == "white"
        assert isinstance(_bf_neg.FS, int | float)
        assert isinstance(_bf_neg.FS_EDGE, int | float)
        assert isinstance(_bf_neg.FS_SMALL, int | float)
        assert isinstance(_bf_neg.FS_TITLE, int | float)
        assert isinstance(_bf_neg.GRAY1, str)
        assert isinstance(_bf_neg.GRAY2, str)
        assert isinstance(_bf_neg.GRAY3, str)
        assert isinstance(_bf_neg.GRAY4, str)
        assert isinstance(_bf_neg.LIGHT_GREEN, str)
        assert isinstance(_bf_neg.LIGHT_RED, str)
        assert isinstance(_bf_neg.LIGHT_YELLOW, str)
        assert isinstance(_bf_neg.LN, str)
        assert isinstance(_bf_neg.OUTPUT_DIR, str)
        assert len(_bf_neg.NEG_EDGES) > 0
        assert len(_bf_neg.NEG_POS) > 0

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

pytestmark = pytest.mark.usefixtures("_no_savefig")

_MOD = "python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram"


# ── Helper functions ───────────────────────────────────────────────────


class TestBFHelpers:
    """Test draw_node, _choose_edge_style, draw_edge, draw_neg_graph."""

    def test_draw_node_default(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_node,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_node(ax, "S", (1, 1))
        plt.close(fig)

    def test_draw_node_current(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_node,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_node(ax, "A", (1, 1), current=True, dist_label="2")
        plt.close(fig)

    def test_draw_node_visited(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_node,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_node(ax, "B", (1, 1), visited=True, dist_label="5")
        plt.close(fig)

    def test_draw_node_error(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_node,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_node(ax, "C", (1, 1), error=True, dist_label="?")
        plt.close(fig)

    def test_draw_node_no_dist_label(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_node,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_node(ax, "X", (1, 1), visited=True)
        plt.close(fig)

    def test_choose_edge_style_cycle(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            _choose_edge_style,
        )

        color, lw, ls = _choose_edge_style(
            negative=False, relaxed=False, highlighted=False, cycle_edge=True
        )
        assert ls == "--"
        assert lw == 2.5

    def test_choose_edge_style_negative(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            _choose_edge_style,
        )

        color, lw, ls = _choose_edge_style(
            negative=True, relaxed=False, highlighted=False, cycle_edge=False
        )
        assert lw == 2.5
        assert ls == "-"

    def test_choose_edge_style_relaxed(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            _choose_edge_style,
        )

        color, lw, ls = _choose_edge_style(
            negative=False, relaxed=True, highlighted=False, cycle_edge=False
        )
        assert lw == 2.5

    def test_choose_edge_style_highlighted(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            _choose_edge_style,
        )

        color, lw, ls = _choose_edge_style(
            negative=False, relaxed=False, highlighted=True, cycle_edge=False
        )
        assert ls == "-"
        assert color == "#1565C0"

    def test_choose_edge_style_default(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            GRAY3,
            _choose_edge_style,
        )

        color, lw, ls = _choose_edge_style(
            negative=False, relaxed=False, highlighted=False, cycle_edge=False
        )
        assert color == GRAY3
        assert lw == 1.5

    def test_draw_edge_no_offset(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_edge,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_edge(ax, (0, 0), (2, 2), 3)
        plt.close(fig)

    def test_draw_edge_with_offset(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_edge,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_edge(ax, (0, 0), (2, 2), -3, negative=True, offset=0.3)
        plt.close(fig)

    def test_draw_edge_highlighted(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_edge,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_edge(ax, (0, 0), (2, 2), 5, highlighted=True)
        plt.close(fig)

    def test_draw_edge_cycle(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_edge,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        draw_edge(ax, (0, 0), (2, 2), -2, cycle_edge=True)
        plt.close(fig)


class TestDrawNegGraph:
    """Test draw_neg_graph with various argument combos."""

    def test_minimal(self) -> None:
        """All-defaults: visited, relaxed, dist, error_nodes all None."""
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            NEG_EDGES,
            draw_neg_graph,
        )

        fig, ax = plt.subplots()
        draw_neg_graph(ax, NEG_EDGES)
        plt.close(fig)

    def test_with_title(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            NEG_EDGES,
            draw_neg_graph,
        )

        fig, ax = plt.subplots()
        draw_neg_graph(ax, NEG_EDGES, title="Test")
        plt.close(fig)

    def test_with_all_options(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            NEG_EDGES,
            NEG_POS,
            draw_neg_graph,
        )

        fig, ax = plt.subplots()
        draw_neg_graph(
            ax,
            NEG_EDGES,
            title="Full",
            dist={"S": "0", "A": "1", "B": "5", "C": "4"},
            current="S",
            visited={"S", "A"},
            relaxed_edges={("S", "A")},
            error_nodes={"C"},
            extra_edges=[("C", "B", -3)],
            node_positions=NEG_POS,
        )
        plt.close(fig)

    def test_explicit_node_positions(self) -> None:
        """Cover node_positions is not None branch."""
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            draw_neg_graph,
        )

        pos = {"X": (1.0, 1.0), "Y": (3.0, 1.0)}
        fig, ax = plt.subplots()
        draw_neg_graph(
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
        from python_pkg.praca_magisterska_video.generate_images._bf_negative_diagrams import (
            generate_bf_negative_weights,
        )

        generate_bf_negative_weights()

    def test_generate_bf_negative_cycle(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._bf_negative_diagrams import (
            generate_bf_negative_cycle,
        )

        generate_bf_negative_cycle()

    def test_add_annotation_box(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._bf_negative_diagrams import (
            _add_annotation_box,
        )

        fig, ax = plt.subplots()
        _add_annotation_box(ax, 1, 1, "test", color="red", bg_color="white")
        plt.close(fig)


class TestBFModuleConstants:
    """Verify module-level constants."""

    def test_constants(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_bf_negative_diagram import (
            BG,
            DPI,
            FS,
            FS_EDGE,
            FS_SMALL,
            FS_TITLE,
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            LIGHT_GREEN,
            LIGHT_RED,
            LIGHT_YELLOW,
            LN,
            NEG_EDGES,
            NEG_POS,
            OUTPUT_DIR,
        )

        assert DPI == 300
        assert BG == "white"
        assert isinstance(FS, int | float)
        assert isinstance(FS_EDGE, int | float)
        assert isinstance(FS_SMALL, int | float)
        assert isinstance(FS_TITLE, int | float)
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(LIGHT_GREEN, str)
        assert isinstance(LIGHT_RED, str)
        assert isinstance(LIGHT_YELLOW, str)
        assert isinstance(LN, str)
        assert isinstance(OUTPUT_DIR, str)
        assert len(NEG_EDGES) > 0
        assert len(NEG_POS) > 0

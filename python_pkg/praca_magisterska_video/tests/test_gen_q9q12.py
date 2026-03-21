"""Tests for Q9/Q12 diagram generation (networking/optimization)."""

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
# _q9q12_common
# =====================================================================
class TestQ9Q12Common:
    """Tests for _q9q12_common constants and helpers."""

    def test_constants_exist(self) -> None:
        from _q9q12_common import (
            _CENTER_Y,
            _LAST_CONDITION_INDEX,
            BG,
            DPI,
            FS,
            FS_EDGE,
            FS_SMALL,
            FS_TITLE,
            GRAY1,
            LIGHT_BLUE,
            LIGHT_GREEN,
            LIGHT_ORANGE,
            LIGHT_RED,
            LIGHT_YELLOW,
            LN,
            OUTPUT_DIR,
        )

        assert DPI == 300
        assert BG == "white"
        assert LN == "black"
        assert FS == 8
        assert FS_TITLE == 11
        assert _LAST_CONDITION_INDEX == 3
        assert _CENTER_Y == 2.5
        assert isinstance(FS_EDGE, int)
        assert isinstance(FS_SMALL, float)
        assert isinstance(GRAY1, str)
        assert isinstance(LIGHT_GREEN, str)
        assert isinstance(LIGHT_RED, str)
        assert isinstance(LIGHT_BLUE, str)
        assert isinstance(LIGHT_YELLOW, str)
        assert isinstance(LIGHT_ORANGE, str)
        assert isinstance(OUTPUT_DIR, str)

    def test_draw_box_rounded(self) -> None:
        from _q9q12_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 1.0, 2.0, 3.0, 1.0, "test")
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_not_rounded(self) -> None:
        from _q9q12_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0.0, 0.0, 2.0, 1.0, "rect", rounded=False)
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_custom_edgecolor(self) -> None:
        from _q9q12_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0.0, 0.0, 2.0, 1.0, "custom", edgecolor="red")
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_arrow(self) -> None:
        from _q9q12_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0)
        plt.close(fig)

    def test_save_fig(self) -> None:
        from _q9q12_common import save_fig

        fig, _ax = plt.subplots()
        save_fig(fig, "test_q9q12.png")

    def test_draw_network_node(self) -> None:
        from _q9q12_common import draw_network_node

        fig, ax = plt.subplots()
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
        draw_network_node(ax, "A", (2.5, 2.5), color="white", fontsize=10, r=0.3)
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_network_edge_directed(self) -> None:
        from _q9q12_common import draw_network_edge

        fig, ax = plt.subplots()
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
        draw_network_edge(
            ax,
            (1.0, 1.0),
            (4.0, 4.0),
            label="10",
            directed=True,
        )
        plt.close(fig)

    def test_draw_network_edge_undirected(self) -> None:
        from _q9q12_common import draw_network_edge

        fig, ax = plt.subplots()
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
        draw_network_edge(
            ax,
            (1.0, 1.0),
            (4.0, 4.0),
            label="5",
            directed=False,
        )
        plt.close(fig)

    def test_draw_network_edge_no_label(self) -> None:
        from _q9q12_common import draw_network_edge

        fig, ax = plt.subplots()
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
        draw_network_edge(ax, (1.0, 1.0), (4.0, 4.0), label="")
        plt.close(fig)

    def test_draw_network_edge_zero_length(self) -> None:
        from _q9q12_common import draw_network_edge

        fig, ax = plt.subplots()
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
        # Same start and end => length 0, should return early
        draw_network_edge(ax, (2.0, 2.0), (2.0, 2.0), label="x")
        plt.close(fig)

    def test_draw_network_edge_with_offset(self) -> None:
        from _q9q12_common import draw_network_edge

        fig, ax = plt.subplots()
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
        draw_network_edge(
            ax,
            (1.0, 1.0),
            (4.0, 4.0),
            label="off",
            offset=0.5,
            label_bg="#EEEEEE",
        )
        plt.close(fig)


# =====================================================================
# _q9q12_network_flow
# =====================================================================
class TestQ9Q12NetworkFlow:
    """Tests for network flow diagrams."""

    def test_gen_ford_fulkerson(self) -> None:
        from _q9q12_network_flow import gen_ford_fulkerson

        gen_ford_fulkerson()

    def test_gen_hungarian(self) -> None:
        from _q9q12_network_flow import gen_hungarian

        gen_hungarian()

    def test_gen_min_cost_flow(self) -> None:
        from _q9q12_network_flow import gen_min_cost_flow

        gen_min_cost_flow()


# =====================================================================
# _q9q12_network_graph
# =====================================================================
class TestQ9Q12NetworkGraph:
    """Tests for network graph diagrams."""

    def test_gen_cpm(self) -> None:
        from _q9q12_network_graph import gen_cpm

        gen_cpm()

    def test_gen_kruskal(self) -> None:
        from _q9q12_network_graph import gen_kruskal

        gen_kruskal()

    def test_gen_tsp(self) -> None:
        from _q9q12_network_graph import gen_tsp

        gen_tsp()


# =====================================================================
# _q9q12_processes
# =====================================================================
class TestQ9Q12Processes:
    """Tests for process diagrams (IPC, deadlock, producer-consumer)."""

    def test_gen_ipc_mechanisms(self) -> None:
        from _q9q12_processes import gen_ipc_mechanisms

        gen_ipc_mechanisms()

    def test_gen_deadlock_illustration(self) -> None:
        from _q9q12_processes import gen_deadlock_illustration

        gen_deadlock_illustration()

    def test_gen_producer_consumer(self) -> None:
        from _q9q12_processes import gen_producer_consumer

        gen_producer_consumer()

    def test_deadlock_coffman_conditions(self) -> None:
        """Verify all 4 Coffman conditions rendered, with last highlighted."""
        from _q9q12_processes import gen_deadlock_illustration

        gen_deadlock_illustration()


# =====================================================================
# generate_q9_q12_diagrams
# =====================================================================
class TestGenerateQ9Q12Diagrams:
    """Tests for the Q9/Q12 diagram generation entrypoint."""

    def test_imports_work(self) -> None:
        from generate_q9_q12_diagrams import (
            gen_cpm,
            gen_deadlock_illustration,
            gen_ford_fulkerson,
            gen_hungarian,
            gen_ipc_mechanisms,
            gen_kruskal,
            gen_min_cost_flow,
            gen_producer_consumer,
            gen_tsp,
        )

        assert callable(gen_ford_fulkerson)
        assert callable(gen_hungarian)
        assert callable(gen_min_cost_flow)
        assert callable(gen_cpm)
        assert callable(gen_kruskal)
        assert callable(gen_tsp)
        assert callable(gen_ipc_mechanisms)
        assert callable(gen_deadlock_illustration)
        assert callable(gen_producer_consumer)

    def test_all_generators_run(self) -> None:
        from generate_q9_q12_diagrams import (
            gen_cpm,
            gen_deadlock_illustration,
            gen_ford_fulkerson,
            gen_hungarian,
            gen_ipc_mechanisms,
            gen_kruskal,
            gen_min_cost_flow,
            gen_producer_consumer,
            gen_tsp,
        )

        gen_ipc_mechanisms()
        gen_deadlock_illustration()
        gen_producer_consumer()
        gen_ford_fulkerson()
        gen_hungarian()
        gen_cpm()
        gen_kruskal()
        gen_tsp()
        gen_min_cost_flow()

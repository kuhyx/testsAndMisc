"""Tests for Q9 diagram generation (concurrency: processes & threads)."""

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
# _q9_common
# =====================================================================
class TestQ9Common:
    """Tests for _q9_common constants and helpers."""

    def test_constants_exist(self) -> None:
        from _q9_common import (
            BG,
            DPI,
            FS,
            FS_LABEL,
            FS_SMALL,
            FS_TITLE,
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            GRAY5,
            LN,
            OCCUPIED_SLOTS,
            OUTPUT_DIR,
        )

        assert DPI == 300
        assert BG == "white"
        assert LN == "black"
        assert FS == 8
        assert FS_TITLE == 11
        assert OCCUPIED_SLOTS == 2
        assert isinstance(FS_SMALL, float)
        assert isinstance(FS_LABEL, int)
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(GRAY5, str)
        assert isinstance(OUTPUT_DIR, str)

    def test_draw_box_rounded(self) -> None:
        from _q9_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 1.0, 2.0, 3.0, 1.0, "test")
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_not_rounded(self) -> None:
        from _q9_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0.0, 0.0, 2.0, 1.0, "rect", rounded=False)
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_custom_edgecolor_linestyle(self) -> None:
        from _q9_common import draw_box

        fig, ax = plt.subplots()
        draw_box(
            ax,
            0.0,
            0.0,
            2.0,
            1.0,
            "custom",
            edgecolor="red",
            linestyle="--",
            rounded=True,
        )
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_not_rounded_custom_linestyle(self) -> None:
        from _q9_common import draw_box

        fig, ax = plt.subplots()
        draw_box(
            ax,
            0.0,
            0.0,
            2.0,
            1.0,
            "dashed",
            edgecolor="blue",
            linestyle="--",
            rounded=False,
        )
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_arrow(self) -> None:
        from _q9_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0)
        plt.close(fig)

    def test_draw_double_arrow(self) -> None:
        from _q9_common import draw_double_arrow

        fig, ax = plt.subplots()
        draw_double_arrow(ax, 0.0, 0.0, 1.0, 1.0)
        plt.close(fig)

    def test_save_fig(self) -> None:
        from _q9_common import save_fig

        fig, _ax = plt.subplots()
        save_fig(fig, "test_output.png")

    def test_draw_table(self) -> None:
        from _q9_common import draw_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        headers = ["A", "B", "C"]
        rows = [["1", "2", "3"], ["4", "5", "6"]]
        draw_table(ax, headers, rows, 0, 1, [2.0, 3.0, 3.0], row_h=0.5)
        assert len(ax.patches) > 0
        plt.close(fig)

    def test_draw_table_custom_fills(self) -> None:
        from _q9_common import draw_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        headers = ["A", "B"]
        rows = [["1", "2"], ["3", "4"]]
        draw_table(
            ax,
            headers,
            rows,
            0,
            1,
            [2.0, 3.0],
            row_fills=["#FF0000", "#00FF00"],
            header_fontsize=10,
        )
        plt.close(fig)

    def test_draw_table_no_header_fontsize(self) -> None:
        from _q9_common import draw_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        draw_table(
            ax,
            ["H1"],
            [["V1"]],
            0,
            1,
            [3.0],
            header_fontsize=None,
        )
        plt.close(fig)


# =====================================================================
# _q9_basics
# =====================================================================
class TestQ9Basics:
    """Tests for the 6 basic process/thread diagrams."""

    def test_gen_process_vs_thread(self) -> None:
        from _q9_basics import gen_process_vs_thread

        gen_process_vs_thread()

    def test_gen_memory_layout(self) -> None:
        from _q9_basics import gen_memory_layout

        gen_memory_layout()

    def test_gen_process_states(self) -> None:
        from _q9_basics import gen_process_states

        gen_process_states()

    def test_gen_thread_structure(self) -> None:
        from _q9_basics import gen_thread_structure

        gen_thread_structure()

    def test_gen_pcb_structure(self) -> None:
        from _q9_basics import gen_pcb_structure

        gen_pcb_structure()

    def test_gen_speed_comparison(self) -> None:
        from _q9_basics import gen_speed_comparison

        gen_speed_comparison()


# =====================================================================
# _q9_classic_sync
# =====================================================================
class TestQ9ClassicSync:
    """Tests for classic sync problems."""

    def test_draw_bounded_buffer_panel(self) -> None:
        from _q9_classic_sync import _draw_bounded_buffer_panel

        fig, ax = plt.subplots()
        _draw_bounded_buffer_panel(ax)
        assert len(ax.patches) > 0
        plt.close(fig)

    def test_draw_readers_writers_panel(self) -> None:
        from _q9_classic_sync import _draw_readers_writers_panel

        fig, ax = plt.subplots()
        _draw_readers_writers_panel(ax)
        assert len(ax.patches) > 0
        plt.close(fig)

    def test_draw_philosophers_panel(self) -> None:
        from _q9_classic_sync import _draw_philosophers_panel

        fig, ax = plt.subplots()
        _draw_philosophers_panel(ax)
        assert len(ax.patches) > 0
        plt.close(fig)

    def test_gen_classic_problems(self) -> None:
        from _q9_classic_sync import gen_classic_problems

        gen_classic_problems()

    def test_gen_sync_comparison(self) -> None:
        from _q9_classic_sync import gen_sync_comparison

        gen_sync_comparison()

    def test_gen_semaphore_concept(self) -> None:
        from _q9_classic_sync import gen_semaphore_concept

        gen_semaphore_concept()


# =====================================================================
# _q9_ipc
# =====================================================================
class TestQ9Ipc:
    """Tests for IPC mechanism diagrams."""

    def test_gen_scenario_table(self) -> None:
        from _q9_ipc import gen_scenario_table

        gen_scenario_table()

    def test_gen_ipc_details(self) -> None:
        from _q9_ipc import gen_ipc_details

        gen_ipc_details()

    def test_gen_ipc_table(self) -> None:
        from _q9_ipc import gen_ipc_table

        gen_ipc_table()


# =====================================================================
# _q9_race_deadlock
# =====================================================================
class TestQ9RaceDeadlock:
    """Tests for race condition, deadlock, and starvation diagrams."""

    def test_gen_race_condition(self) -> None:
        from _q9_race_deadlock import gen_race_condition

        gen_race_condition()

    def test_gen_deadlock_scenario(self) -> None:
        from _q9_race_deadlock import gen_deadlock_scenario

        gen_deadlock_scenario()

    def test_gen_coffman_strategies(self) -> None:
        from _q9_race_deadlock import gen_coffman_strategies

        gen_coffman_strategies()

    def test_gen_starvation_priority(self) -> None:
        from _q9_race_deadlock import gen_starvation_priority

        gen_starvation_priority()


# =====================================================================
# generate_q9_all_diagrams
# =====================================================================
class TestGenerateQ9AllDiagrams:
    """Tests for the Q9 diagram generation entrypoint."""

    def test_module_exports(self) -> None:
        from generate_q9_all_diagrams import __all__

        expected = [
            "gen_classic_problems",
            "gen_coffman_strategies",
            "gen_deadlock_scenario",
            "gen_ipc_details",
            "gen_ipc_table",
            "gen_memory_layout",
            "gen_pcb_structure",
            "gen_process_states",
            "gen_process_vs_thread",
            "gen_race_condition",
            "gen_scenario_table",
            "gen_semaphore_concept",
            "gen_speed_comparison",
            "gen_starvation_priority",
            "gen_sync_comparison",
            "gen_thread_structure",
        ]
        assert sorted(__all__) == sorted(expected)

    def test_all_functions_callable(self) -> None:
        import generate_q9_all_diagrams as mod

        for name in mod.__all__:
            assert callable(getattr(mod, name))

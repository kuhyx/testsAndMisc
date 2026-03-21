"""Tests for scheduling diagram generation."""

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
# _sched_common
# =====================================================================
class TestSchedCommon:
    """Tests for scheduling common constants and helpers."""

    def test_constants_exist(self) -> None:
        from _sched_common import (
            BG,
            DPI,
            FONTWEIGHT_THRESHOLD,
            FS,
            FS_TITLE,
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            GRAY5,
            LN,
            MIN_COLUMN_INDEX,
            OUTPUT_DIR,
        )

        assert DPI == 300
        assert BG == "white"
        assert LN == "black"
        assert FS == 8
        assert FS_TITLE == 11
        assert MIN_COLUMN_INDEX == 3
        assert FONTWEIGHT_THRESHOLD == 3
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(GRAY5, str)
        assert isinstance(OUTPUT_DIR, str)

    def test_draw_box_rounded(self) -> None:
        from _sched_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 1.0, 2.0, 3.0, 1.0, "test")
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_not_rounded(self) -> None:
        from _sched_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0.0, 0.0, 2.0, 1.0, "rect", rounded=False)
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_custom_params(self) -> None:
        from _sched_common import draw_box

        fig, ax = plt.subplots()
        draw_box(
            ax,
            0.0,
            0.0,
            2.0,
            1.0,
            "custom",
            fill="red",
            lw=2.0,
            fontsize=12,
            fontweight="bold",
            ha="left",
            va="top",
            rounded=True,
        )
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_arrow(self) -> None:
        from _sched_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0)
        plt.close(fig)

    def test_draw_arrow_custom(self) -> None:
        from _sched_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0, lw=2.0, style="<->", color="red")
        plt.close(fig)


# =====================================================================
# _sched_complexity_edd
# =====================================================================
class TestSchedComplexityEdd:
    """Tests for complexity map and EDD example."""

    def test_draw_complexity_map(self) -> None:
        from _sched_complexity_edd import draw_complexity_map

        draw_complexity_map()

    def test_draw_edd_example(self) -> None:
        from _sched_complexity_edd import draw_edd_example

        draw_edd_example()


# =====================================================================
# _sched_graham
# =====================================================================
class TestSchedGraham:
    """Tests for Graham notation diagram."""

    def test_draw_graham_notation(self) -> None:
        from _sched_graham import draw_graham_notation

        draw_graham_notation()

    def test_draw_graham_formula_bar(self) -> None:
        from _sched_graham import _draw_graham_formula_bar

        fig, ax = plt.subplots()
        _draw_graham_formula_bar(ax)
        assert len(ax.patches) >= 3
        plt.close(fig)

    def test_draw_graham_alpha_beta(self) -> None:
        from _sched_graham import _draw_graham_alpha_beta

        fig, ax = plt.subplots()
        _draw_graham_alpha_beta(ax)
        assert len(ax.patches) >= 7
        plt.close(fig)

    def test_draw_graham_lower(self) -> None:
        from _sched_graham import _draw_graham_lower

        fig, ax = plt.subplots()
        _draw_graham_lower(ax)
        assert len(ax.patches) >= 6
        plt.close(fig)


# =====================================================================
# _sched_johnson
# =====================================================================
class TestSchedJohnson:
    """Tests for Johnson Gantt chart diagram."""

    def test_draw_johnson_gantt(self) -> None:
        from _sched_johnson import draw_johnson_gantt

        draw_johnson_gantt()

    def test_draw_johnson_decision_table(self) -> None:
        from _sched_johnson import _draw_johnson_decision_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 5)
        _draw_johnson_decision_table(ax)
        assert len(ax.patches) >= 6
        plt.close(fig)

    def test_draw_johnson_gantt_chart(self) -> None:
        from _sched_johnson import _draw_johnson_gantt_chart

        fig, ax = plt.subplots()
        ax.set_xlim(-1, 24)
        ax.set_ylim(-1, 4)
        _draw_johnson_gantt_chart(ax)
        assert len(ax.patches) >= 10
        plt.close(fig)


# =====================================================================
# _sched_spt_flow_job
# =====================================================================
class TestSchedSptFlowJob:
    """Tests for SPT comparison and flow vs job shop diagrams."""

    def test_draw_spt_comparison(self) -> None:
        from _sched_spt_flow_job import draw_spt_comparison

        draw_spt_comparison()

    def test_draw_flow_vs_job(self) -> None:
        from _sched_spt_flow_job import draw_flow_vs_job

        draw_flow_vs_job()

    def test_draw_flow_shop(self) -> None:
        from _sched_spt_flow_job import _draw_flow_shop

        fig, ax = plt.subplots()
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        _draw_flow_shop(ax)
        assert len(ax.patches) >= 3
        plt.close(fig)

    def test_draw_job_shop(self) -> None:
        from _sched_spt_flow_job import _draw_job_shop

        fig, ax = plt.subplots()
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        _draw_job_shop(ax)
        assert len(ax.patches) >= 3
        plt.close(fig)


# =====================================================================
class TestGenerateSchedulingDiagrams:
    """Tests for generate_scheduling_diagrams entrypoint."""

    def test_all_exports(self) -> None:
        import generate_scheduling_diagrams as mod

        for name in mod.__all__:
            assert hasattr(mod, name)

    def test_reexported_constants(self) -> None:
        import generate_scheduling_diagrams as mod

        assert mod.DPI == 300
        assert mod.MIN_COLUMN_INDEX == 3
        assert mod.FONTWEIGHT_THRESHOLD == 3

    def test_reexported_generators_callable(self) -> None:
        import generate_scheduling_diagrams as mod

        assert callable(mod.draw_complexity_map)
        assert callable(mod.draw_edd_example)
        assert callable(mod.draw_graham_notation)
        assert callable(mod.draw_johnson_gantt)
        assert callable(mod.draw_spt_comparison)
        assert callable(mod.draw_flow_vs_job)

"""Tests for Q20 stream-processing diagram modules (GROUP 4).

Covers:
  - _q20_common.py (draw_box, draw_arrow, save_fig, draw_table, constants)
  - _q20_batch_and_windows.py (gen_batch_vs_streaming, gen_window_types,
     _draw_tumbling_window, _draw_sliding_window, _draw_session_window,
     _draw_global_window)
  - _q20_time_monitoring_sessions.py (gen_event_vs_processing_time,
     gen_tumbling_fraud, gen_sliding_sla, gen_session_users)
  - _q20_platforms.py (gen_streaming_ecosystem, gen_true_vs_microbatch,
     gen_platform_comparison, gen_kafka_streams_arch, gen_flink_arch)
  - _q20_architectures.py (gen_spark_streaming_arch, gen_lambda_vs_kappa,
     gen_lambda_kappa_table, gen_exactly_once)
  - _q20_late_and_decisions.py (gen_late_data_strategies, gen_decision_tree)
  - generate_q20_diagrams.py (__all__, imports)
"""

from __future__ import annotations

import importlib

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")


# ── _q20_common ───────────────────────────────────────────────────────


class TestQ20Constants:
    """Module-level constants."""

    def test_dpi(self) -> None:
        from _q20_common import DPI

        assert DPI == 300

    def test_output_dir(self) -> None:
        from _q20_common import OUTPUT_DIR

        assert isinstance(OUTPUT_DIR, str)

    def test_grays(self) -> None:
        from _q20_common import GRAY1, GRAY2, GRAY3, GRAY4, GRAY5

        assert all(isinstance(g, str) for g in [GRAY1, GRAY2, GRAY3, GRAY4, GRAY5])


class TestQ20DrawBox:
    """draw_box from _q20_common."""

    def test_rounded(self) -> None:
        from _q20_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0, 0, 2, 1, "test")
        plt.close(fig)

    def test_not_rounded(self) -> None:
        from _q20_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0, 0, 2, 1, "test", rounded=False)
        plt.close(fig)

    def test_custom_style(self) -> None:
        from _q20_common import draw_box

        fig, ax = plt.subplots()
        draw_box(
            ax,
            0,
            0,
            2,
            1,
            "test",
            fill="#CCC",
            lw=2.0,
            fontsize=12,
            fontweight="bold",
            ha="left",
            va="top",
            edgecolor="red",
            linestyle="--",
        )
        plt.close(fig)


class TestQ20DrawArrow:
    """draw_arrow from _q20_common."""

    def test_default(self) -> None:
        from _q20_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1)
        plt.close(fig)

    def test_custom(self) -> None:
        from _q20_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1, lw=2.5, style="<->", color="red")
        plt.close(fig)


class TestQ20SaveFig:
    """save_fig from _q20_common."""

    def test_save(self) -> None:
        from _q20_common import save_fig

        fig, _ax = plt.subplots()
        save_fig(fig, "test_q20.png")


class TestQ20DrawTable:
    """draw_table from _q20_common."""

    def test_basic(self) -> None:
        from _q20_common import draw_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        draw_table(ax, ["A", "B"], [["1", "2"]], 0, 0, [2.0, 2.0])
        plt.close(fig)

    def test_custom_fills(self) -> None:
        from _q20_common import draw_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        draw_table(
            ax,
            ["X"],
            [["a"], ["b"], ["c"]],
            0,
            0,
            [3.0],
            row_h=0.5,
            row_fills=["#EEE", "#DDD"],
            header_fontsize=10,
        )
        plt.close(fig)

    def test_row_fills_shorter_than_rows(self) -> None:
        """row_fills has fewer entries than rows → falls through condition."""
        from _q20_common import draw_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-10, 2)
        draw_table(
            ax,
            ["H"],
            [["r1"], ["r2"], ["r3"], ["r4"]],
            0,
            0,
            [3.0],
            row_fills=["#AAA"],
        )
        plt.close(fig)

    def test_no_row_fills(self) -> None:
        """row_fills=None → alternating GRAY4/white."""
        from _q20_common import draw_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        draw_table(ax, ["H"], [["r1"], ["r2"]], 0, 0, [3.0])
        plt.close(fig)


# ── _q20_batch_and_windows ────────────────────────────────────────────


class TestBatchVsStreaming:
    """gen_batch_vs_streaming."""

    def test_runs(self) -> None:
        from _q20_batch_and_windows import gen_batch_vs_streaming

        gen_batch_vs_streaming()


class TestWindowTypes:
    """gen_window_types with sub-helpers."""

    def test_runs(self) -> None:
        from _q20_batch_and_windows import gen_window_types

        gen_window_types()

    def test_tumbling_window(self) -> None:
        from _q20_batch_and_windows import _draw_tumbling_window

        fig, ax = plt.subplots()
        _draw_tumbling_window(ax, list(range(1, 13)))
        plt.close(fig)

    def test_sliding_window(self) -> None:
        from _q20_batch_and_windows import _draw_sliding_window

        fig, ax = plt.subplots()
        _draw_sliding_window(ax, list(range(1, 13)))
        plt.close(fig)

    def test_session_window(self) -> None:
        from _q20_batch_and_windows import _draw_session_window

        fig, ax = plt.subplots()
        _draw_session_window(ax)
        plt.close(fig)

    def test_global_window(self) -> None:
        from _q20_batch_and_windows import _draw_global_window

        fig, ax = plt.subplots()
        _draw_global_window(ax)
        plt.close(fig)


# ── _q20_time_monitoring_sessions ─────────────────────────────────────


class TestEventVsProcessingTime:
    """gen_event_vs_processing_time."""

    def test_runs(self) -> None:
        from _q20_time_monitoring_sessions import gen_event_vs_processing_time

        gen_event_vs_processing_time()


class TestTumblingFraud:
    """gen_tumbling_fraud."""

    def test_runs(self) -> None:
        from _q20_time_monitoring_sessions import gen_tumbling_fraud

        gen_tumbling_fraud()


class TestSlidingSla:
    """gen_sliding_sla."""

    def test_runs(self) -> None:
        from _q20_time_monitoring_sessions import gen_sliding_sla

        gen_sliding_sla()


class TestSessionUsers:
    """gen_session_users."""

    def test_runs(self) -> None:
        from _q20_time_monitoring_sessions import gen_session_users

        gen_session_users()


# ── _q20_platforms ────────────────────────────────────────────────────


class TestStreamingEcosystem:
    """gen_streaming_ecosystem."""

    def test_runs(self) -> None:
        from _q20_platforms import gen_streaming_ecosystem

        gen_streaming_ecosystem()


class TestTrueVsMicrobatch:
    """gen_true_vs_microbatch."""

    def test_runs(self) -> None:
        from _q20_platforms import gen_true_vs_microbatch

        gen_true_vs_microbatch()


class TestPlatformComparison:
    """gen_platform_comparison."""

    def test_runs(self) -> None:
        from _q20_platforms import gen_platform_comparison

        gen_platform_comparison()


class TestKafkaStreamsArch:
    """gen_kafka_streams_arch."""

    def test_runs(self) -> None:
        from _q20_platforms import gen_kafka_streams_arch

        gen_kafka_streams_arch()


class TestFlinkArch:
    """gen_flink_arch."""

    def test_runs(self) -> None:
        from _q20_platforms import gen_flink_arch

        gen_flink_arch()


# ── _q20_architectures ───────────────────────────────────────────────


class TestSparkStreamingArch:
    """gen_spark_streaming_arch."""

    def test_runs(self) -> None:
        from _q20_architectures import gen_spark_streaming_arch

        gen_spark_streaming_arch()


class TestLambdaVsKappa:
    """gen_lambda_vs_kappa."""

    def test_runs(self) -> None:
        from _q20_architectures import gen_lambda_vs_kappa

        gen_lambda_vs_kappa()


class TestLambdaKappaTable:
    """gen_lambda_kappa_table."""

    def test_runs(self) -> None:
        from _q20_architectures import gen_lambda_kappa_table

        gen_lambda_kappa_table()


class TestExactlyOnce:
    """gen_exactly_once."""

    def test_runs(self) -> None:
        from _q20_architectures import gen_exactly_once

        gen_exactly_once()


# ── _q20_late_and_decisions ───────────────────────────────────────────


class TestLateDataStrategies:
    """gen_late_data_strategies."""

    def test_runs(self) -> None:
        from _q20_late_and_decisions import gen_late_data_strategies

        gen_late_data_strategies()


class TestDecisionTree:
    """gen_decision_tree."""

    def test_runs(self) -> None:
        from _q20_late_and_decisions import gen_decision_tree

        gen_decision_tree()


# ── generate_q20_diagrams ────────────────────────────────────────────


class TestGenerateQ20Module:
    """Test module imports and __all__."""

    def test_imports(self) -> None:
        importlib.import_module("generate_q20_diagrams")

    def test_all_length(self) -> None:
        import generate_q20_diagrams

        assert len(generate_q20_diagrams.__all__) == 17

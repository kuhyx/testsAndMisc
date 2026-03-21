"""Tests for study diagram generators."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

# _study_vision uses scipy.stats.norm.cdf - patch it in fixtures instead of
# polluting sys.modules (which breaks other packages that import scipy).


@pytest.fixture(autouse=True)
def _patch_savefig(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent matplotlib from writing files to disk."""
    monkeypatch.setattr(mpl.figure.Figure, "savefig", lambda *_a, **_kw: None)
    monkeypatch.setattr(plt, "savefig", lambda *_a, **_kw: None)


# =====================================================================
class TestStudyDiagrams:
    """Tests for generate_study_diagrams constants and helpers."""

    def test_constants_exist(self) -> None:
        from generate_study_diagrams import (
            BG,
            DPI,
            FS,
            FS_TITLE,
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            GRAY5,
            LN,
            OUTPUT_DIR,
        )

        assert DPI == 300
        assert BG == "white"
        assert LN == "black"
        assert FS == 8
        assert FS_TITLE == 12
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(GRAY5, str)
        assert isinstance(OUTPUT_DIR, str)

    def test_draw_box_rounded(self) -> None:
        from generate_study_diagrams import draw_box

        _fig, ax = plt.subplots()
        draw_box(ax, 1.0, 2.0, 3.0, 1.0, "test box")
        plt.close()

    def test_draw_box_not_rounded(self) -> None:
        from generate_study_diagrams import draw_box

        _fig, ax = plt.subplots()
        draw_box(ax, 1.0, 2.0, 3.0, 1.0, "rect", rounded=False)
        plt.close()

    def test_draw_box_custom_params(self) -> None:
        from generate_study_diagrams import draw_box

        _fig, ax = plt.subplots()
        draw_box(
            ax,
            0.0,
            0.0,
            2.0,
            1.0,
            "custom",
            fill="#FF0000",
            lw=2.0,
            fontsize=10.0,
            fontweight="bold",
            ha="left",
            va="top",
        )
        plt.close()

    def test_draw_arrow(self) -> None:
        from generate_study_diagrams import draw_arrow

        _fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 5.0, 3.0)
        plt.close()

    def test_draw_arrow_custom(self) -> None:
        from generate_study_diagrams import draw_arrow

        _fig, ax = plt.subplots()
        draw_arrow(ax, 1.0, 1.0, 4.0, 2.0, lw=2.0, style="<->", color="#FF0000")
        plt.close()


# =====================================================================
# _study_consensus
# =====================================================================
class TestStudyConsensus:
    """Tests for _study_consensus diagram functions."""

    def test_draw_linearizability_vs_sequential(self) -> None:
        from _study_consensus import draw_linearizability_vs_sequential

        draw_linearizability_vs_sequential()

    def test_draw_paxos_flow(self) -> None:
        from _study_consensus import draw_paxos_flow

        draw_paxos_flow()


# =====================================================================
# _study_network
# =====================================================================
class TestStudyNetwork:
    """Tests for _study_network diagram functions."""

    def test_draw_network_models(self) -> None:
        from _study_network import draw_network_models

        draw_network_models()

    def test_draw_vector_clock_timeline(self) -> None:
        from _study_network import draw_vector_clock_timeline

        draw_vector_clock_timeline()


# =====================================================================
# _study_vision
# =====================================================================
class TestStudyVision:
    """Tests for _study_vision diagram functions."""

    def test_draw_hog_pipeline(self) -> None:
        from _study_vision import draw_hog_pipeline

        draw_hog_pipeline()

    def test_draw_rcnn_evolution(self) -> None:
        from _study_vision import draw_rcnn_evolution

        draw_rcnn_evolution()

    def test_draw_segmentation_types(self) -> None:
        from _study_vision import draw_segmentation_types

        draw_segmentation_types()

    def test_draw_fsd_ssd(self) -> None:
        from _study_vision import draw_fsd_ssd

        draw_fsd_ssd()

    def test_draw_instance_panel(self) -> None:
        from _study_vision import _draw_instance_panel

        _fig, ax = plt.subplots()
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        _draw_instance_panel(ax)
        plt.close()

    def test_draw_panoptic_panel(self) -> None:
        from _study_vision import _draw_panoptic_panel

        _fig, ax = plt.subplots()
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        _draw_panoptic_panel(ax)
        plt.close()

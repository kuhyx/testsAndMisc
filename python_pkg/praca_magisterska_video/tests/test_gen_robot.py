"""Tests for robot language diagram generation."""

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
# generate_robot_lang_diagrams (common helpers + entrypoint)
# =====================================================================
class TestRobotLangCommon:
    """Tests for generate_robot_lang_diagrams constants and helpers."""

    def test_constants_exist(self) -> None:
        from generate_robot_lang_diagrams import (
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
            WHITE,
        )

        assert DPI == 300
        assert BG == "white"
        assert LN == "black"
        assert FS == 8
        assert FS_TITLE == 11
        assert WHITE == "white"
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(GRAY5, str)
        assert isinstance(OUTPUT_DIR, str)

    def test_draw_box_rounded(self) -> None:
        from generate_robot_lang_diagrams import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 1.0, 2.0, 3.0, 1.0, "test")
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_not_rounded(self) -> None:
        from generate_robot_lang_diagrams import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0.0, 0.0, 2.0, 1.0, "rect", rounded=False)
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_custom_params(self) -> None:
        from generate_robot_lang_diagrams import draw_box

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
        from generate_robot_lang_diagrams import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0)
        plt.close(fig)

    def test_draw_arrow_custom(self) -> None:
        from generate_robot_lang_diagrams import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0, lw=2.0, style="<->", color="red")
        plt.close(fig)


# =====================================================================
# _robot_movement_ros
# =====================================================================
class TestRobotMovementRos:
    """Tests for movement types and online/offline diagrams."""

    def test_draw_ptp_subplot(self) -> None:
        from _robot_movement_ros import _draw_ptp_subplot

        fig, ax = plt.subplots()
        _draw_ptp_subplot(ax)
        plt.close(fig)

    def test_draw_lin_subplot(self) -> None:
        from _robot_movement_ros import _draw_lin_subplot

        fig, ax = plt.subplots()
        _draw_lin_subplot(ax)
        plt.close(fig)

    def test_draw_circ_subplot(self) -> None:
        from _robot_movement_ros import _draw_circ_subplot

        fig, ax = plt.subplots()
        _draw_circ_subplot(ax)
        plt.close(fig)

    def test_draw_movement_types(self) -> None:
        from _robot_movement_ros import draw_movement_types

        draw_movement_types()

    def test_draw_online_offline(self) -> None:
        from _robot_movement_ros import draw_online_offline

        draw_online_offline()


# =====================================================================
# _robot_pyramid_vendor
# =====================================================================
class TestRobotPyramidVendor:
    """Tests for TRMS pyramid and vendor comparison diagrams."""

    def test_draw_trms_pyramid(self) -> None:
        from _robot_pyramid_vendor import draw_trms_pyramid

        draw_trms_pyramid()

    def test_draw_vendor_comparison(self) -> None:
        from _robot_pyramid_vendor import draw_vendor_comparison

        draw_vendor_comparison()


# =====================================================================
# _robot_ros_rapid
# =====================================================================
class TestRobotRosRapid:
    """Tests for ROS architecture and RAPID structure diagrams."""

    def test_draw_ros_architecture(self) -> None:
        from _robot_ros_rapid import draw_ros_architecture

        draw_ros_architecture()

    def test_draw_rapid_structure(self) -> None:
        from _robot_ros_rapid import draw_rapid_structure

        draw_rapid_structure()

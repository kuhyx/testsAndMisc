"""Tests for Pub/Sub diagram modules (GROUP 3).

Covers:
  - _pubsub_common.py (BoxStyle, ArrowCfg, DashedCfg, draw_box, draw_arrow,
                        draw_dashed_arrow, draw_cross, draw_check, save)
  - _pubsub_qos.py (draw_qos_at_most_once, draw_qos_at_least_once,
                     draw_qos_exactly_once)
  - _pubsub_topic_content.py (draw_sub_topic, draw_sub_content)
  - _pubsub_type_hierarchical.py (draw_sub_type, draw_sub_hierarchical)
  - generate_pubsub_diagrams.py (imports only, __name__ guard)
"""

from __future__ import annotations

import importlib

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")


# ── _pubsub_common ────────────────────────────────────────────────────


class TestPubsubCommonDataclasses:
    """BoxStyle, ArrowCfg, DashedCfg dataclass defaults."""

    def test_box_style_defaults(self) -> None:
        from _pubsub_common import BoxStyle

        bs = BoxStyle()
        assert bs.fill == "white"
        assert bs.rounded is True
        assert bs.fontweight == "normal"

    def test_box_style_custom(self) -> None:
        from _pubsub_common import BoxStyle

        bs = BoxStyle(fill="red", rounded=False, fontweight="bold")
        assert bs.fill == "red"
        assert bs.rounded is False

    def test_arrow_cfg_defaults(self) -> None:
        from _pubsub_common import ArrowCfg

        ac = ArrowCfg()
        assert ac.style == "->"
        assert ac.label == ""

    def test_arrow_cfg_custom(self) -> None:
        from _pubsub_common import ArrowCfg

        ac = ArrowCfg(label="test", label_fs=12, lw=2.0)
        assert ac.label == "test"
        assert ac.label_fs == 12

    def test_dashed_cfg_defaults(self) -> None:
        from _pubsub_common import DashedCfg

        dc = DashedCfg()
        assert dc.label == ""

    def test_dashed_cfg_custom(self) -> None:
        from _pubsub_common import DashedCfg

        dc = DashedCfg(label="dashed", lw=2.0)
        assert dc.label == "dashed"


class TestPubsubDrawBox:
    """draw_box from _pubsub_common."""

    def test_rounded(self) -> None:
        from _pubsub_common import BoxStyle, draw_box

        fig, ax = plt.subplots()
        draw_box(ax, (0, 0), (2, 1), "test", BoxStyle())
        plt.close(fig)

    def test_not_rounded(self) -> None:
        from _pubsub_common import BoxStyle, draw_box

        fig, ax = plt.subplots()
        draw_box(ax, (0, 0), (2, 1), "test", BoxStyle(rounded=False))
        plt.close(fig)

    def test_no_style(self) -> None:
        from _pubsub_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, (0, 0), (2, 1), "test")
        plt.close(fig)


class TestPubsubDrawArrow:
    """draw_arrow from _pubsub_common."""

    def test_default(self) -> None:
        from _pubsub_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, (0, 0), (1, 1))
        plt.close(fig)

    def test_with_label(self) -> None:
        from _pubsub_common import ArrowCfg, draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, (0, 0), (1, 1), ArrowCfg(label="MSG"))
        plt.close(fig)

    def test_no_label(self) -> None:
        from _pubsub_common import ArrowCfg, draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, (0, 0), (1, 1), ArrowCfg(label=""))
        plt.close(fig)


class TestPubsubDrawDashedArrow:
    """draw_dashed_arrow from _pubsub_common."""

    def test_default(self) -> None:
        from _pubsub_common import draw_dashed_arrow

        fig, ax = plt.subplots()
        draw_dashed_arrow(ax, (0, 0), (1, 1))
        plt.close(fig)

    def test_with_label(self) -> None:
        from _pubsub_common import DashedCfg, draw_dashed_arrow

        fig, ax = plt.subplots()
        draw_dashed_arrow(ax, (0, 0), (1, 1), DashedCfg(label="lost"))
        plt.close(fig)

    def test_no_label(self) -> None:
        from _pubsub_common import DashedCfg, draw_dashed_arrow

        fig, ax = plt.subplots()
        draw_dashed_arrow(ax, (0, 0), (1, 1), DashedCfg(label=""))
        plt.close(fig)


class TestPubsubDrawCross:
    """draw_cross from _pubsub_common."""

    def test_default(self) -> None:
        from _pubsub_common import draw_cross

        fig, ax = plt.subplots()
        draw_cross(ax, (5, 5))
        plt.close(fig)

    def test_custom(self) -> None:
        from _pubsub_common import draw_cross

        fig, ax = plt.subplots()
        draw_cross(ax, (5, 5), size=0.3, lw=3.0, color="red")
        plt.close(fig)


class TestPubsubDrawCheck:
    """draw_check from _pubsub_common."""

    def test_default(self) -> None:
        from _pubsub_common import draw_check

        fig, ax = plt.subplots()
        draw_check(ax, (5, 5))
        plt.close(fig)

    def test_custom(self) -> None:
        from _pubsub_common import draw_check

        fig, ax = plt.subplots()
        draw_check(ax, (5, 5), size=0.3, lw=3.0, color="green")
        plt.close(fig)


class TestPubsubSave:
    """save from _pubsub_common."""

    def test_save(self) -> None:
        from _pubsub_common import save

        fig, _ax = plt.subplots()
        save(fig, "test_output.png")


class TestPubsubConstants:
    """Module-level constants from _pubsub_common."""

    def test_dpi(self) -> None:
        from _pubsub_common import DPI

        assert DPI == 300

    def test_fig_w(self) -> None:
        from _pubsub_common import FIG_W

        assert FIG_W == 8.27

    def test_output_dir(self) -> None:
        from _pubsub_common import OUTPUT_DIR

        assert isinstance(OUTPUT_DIR, str)


# ── _pubsub_qos ───────────────────────────────────────────────────────


class TestQosAtMostOnce:
    """draw_qos_at_most_once."""

    def test_runs(self) -> None:
        from _pubsub_qos import draw_qos_at_most_once

        draw_qos_at_most_once()


class TestQosAtLeastOnce:
    """draw_qos_at_least_once."""

    def test_runs(self) -> None:
        from _pubsub_qos import draw_qos_at_least_once

        draw_qos_at_least_once()


class TestQosExactlyOnce:
    """draw_qos_exactly_once."""

    def test_runs(self) -> None:
        from _pubsub_qos import draw_qos_exactly_once

        draw_qos_exactly_once()


# ── _pubsub_topic_content ─────────────────────────────────────────────


class TestSubTopic:
    """draw_sub_topic."""

    def test_runs(self) -> None:
        from _pubsub_topic_content import draw_sub_topic

        draw_sub_topic()


class TestSubContent:
    """draw_sub_content."""

    def test_runs(self) -> None:
        from _pubsub_topic_content import draw_sub_content

        draw_sub_content()


# ── _pubsub_type_hierarchical ─────────────────────────────────────────


class TestSubType:
    """draw_sub_type."""

    def test_runs(self) -> None:
        from _pubsub_type_hierarchical import draw_sub_type

        draw_sub_type()


class TestSubHierarchical:
    """draw_sub_hierarchical."""

    def test_runs(self) -> None:
        from _pubsub_type_hierarchical import draw_sub_hierarchical

        draw_sub_hierarchical()


# ── generate_pubsub_diagrams ──────────────────────────────────────────


class TestGeneratePubsubModule:
    """Test that the module is importable."""

    def test_imports(self) -> None:
        importlib.import_module("generate_pubsub_diagrams")

"""Tests for agent diagram modules (GROUP 1).

Covers:
  - generate_agent_diagrams.py (helpers, dataclasses)
  - _agent_reactive.py (draw_see_think_act, draw_3t_architecture)
  - _agent_cognitive.py (draw_behavior_tree, draw_bdi_model)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

from python_pkg.praca_magisterska_video.generate_images._agent_cognitive import (
    draw_bdi_model,
    draw_behavior_tree,
)
from python_pkg.praca_magisterska_video.generate_images._agent_reactive import (
    draw_3t_architecture,
    draw_see_think_act,
)
from python_pkg.praca_magisterska_video.generate_images.generate_agent_diagrams import (
    BG,
    DPI,
    GRAY5,
    OUTPUT_DIR,
    ArrowCfg,
    BoxStyle,
    DashedArrowCfg,
    draw_arrow,
    draw_box,
    draw_dashed_arrow,
)

pytestmark = pytest.mark.usefixtures("_no_savefig")

_MOD = "python_pkg.praca_magisterska_video.generate_images"


# ── helpers in generate_agent_diagrams ──────────────────────────────────


class TestAgentHelpers:
    """Test draw_box, draw_arrow, draw_dashed_arrow and dataclasses."""

    def test_draw_box_rounded(self) -> None:
        fig, ax = plt.subplots()
        draw_box(ax, (0, 0), (1, 1), "hi", BoxStyle(rounded=True))
        plt.close(fig)

    def test_draw_box_not_rounded(self) -> None:
        fig, ax = plt.subplots()
        draw_box(ax, (0, 0), (1, 1), "hi", BoxStyle(rounded=False))
        plt.close(fig)

    def test_draw_box_no_style(self) -> None:
        fig, ax = plt.subplots()
        draw_box(ax, (0, 0), (1, 1), "hi")
        plt.close(fig)

    def test_draw_arrow_with_label(self) -> None:
        fig, ax = plt.subplots()
        draw_arrow(ax, (0, 0), (1, 1), ArrowCfg(label="lbl"))
        plt.close(fig)

    def test_draw_arrow_no_label(self) -> None:
        fig, ax = plt.subplots()
        draw_arrow(ax, (0, 0), (1, 1))
        plt.close(fig)

    def test_draw_dashed_arrow_with_label(self) -> None:
        fig, ax = plt.subplots()
        draw_dashed_arrow(ax, (0, 0), (1, 1), DashedArrowCfg(label="lbl"))
        plt.close(fig)

    def test_draw_dashed_arrow_no_label(self) -> None:
        fig, ax = plt.subplots()
        draw_dashed_arrow(ax, (0, 0), (1, 1))
        plt.close(fig)

    def test_dataclass_defaults(self) -> None:
        bs = BoxStyle()
        assert bs.rounded is True
        assert bs.fill == "white"
        ac = ArrowCfg()
        assert ac.label == ""
        dc = DashedArrowCfg()
        assert dc.label == ""

    def test_module_constants(self) -> None:
        assert DPI == 300
        assert BG == "white"
        assert isinstance(GRAY5, str)
        assert isinstance(OUTPUT_DIR, str)


# ── _agent_reactive ────────────────────────────────────────────────────


class TestAgentReactive:
    """Test draw_see_think_act and draw_3t_architecture."""

    def test_draw_see_think_act(self) -> None:
        draw_see_think_act()

    def test_draw_3t_architecture(self) -> None:
        draw_3t_architecture()


# ── _agent_cognitive ───────────────────────────────────────────────────


class TestAgentCognitive:
    """Test draw_behavior_tree (covers all node types) and draw_bdi_model."""

    def test_draw_behavior_tree(self) -> None:
        draw_behavior_tree()

    def test_draw_bdi_model(self) -> None:
        draw_bdi_model()

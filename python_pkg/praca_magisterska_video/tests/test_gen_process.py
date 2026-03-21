"""Tests for process diagram modules (GROUP 2).

Covers:
  - generate_process_diagrams.py (draw_arrow, draw_line, draw_rounded_rect,
                                   draw_diamond, constants)
  - _process_bpmn_uml.py (generate_bpmn, generate_uml_activity, and sub-helpers)
  - _process_epc_fc.py (generate_epc and sub-helpers)
  - _process_fc.py (generate_flowchart and sub-helpers)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")

_GEN = "python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams"
_BPMN = "python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml"
_EPC = "python_pkg.praca_magisterska_video.generate_images._process_epc_fc"
_FC = "python_pkg.praca_magisterska_video.generate_images._process_fc"


# ── generate_process_diagrams helpers ──────────────────────────────────


class TestProcessConstants:
    """Constants and module-level values."""

    def test_dpi(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            DPI,
        )

        assert DPI == 300

    def test_bg_color(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            BG_COLOR,
        )

        assert BG_COLOR == "white"

    def test_output_dir(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            OUTPUT_DIR,
        )

        assert isinstance(OUTPUT_DIR, str)


class TestProcessDrawArrow:
    """Test draw_arrow helper."""

    def test_default(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            draw_arrow,
        )

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1)
        plt.close(fig)


class TestProcessDrawLine:
    """Test draw_line helper."""

    def test_default(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            draw_line,
        )

        fig, ax = plt.subplots()
        draw_line(ax, 0, 0, 5, 5)
        plt.close(fig)


class TestProcessDrawRoundedRect:
    """Test draw_rounded_rect helper."""

    def test_default(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            draw_rounded_rect,
        )

        fig, ax = plt.subplots()
        draw_rounded_rect(ax, 5, 5, 10, 4, "Hello")
        plt.close(fig)

    def test_custom_params(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            draw_rounded_rect,
        )

        fig, ax = plt.subplots()
        draw_rounded_rect(ax, 0, 0, 8, 3, "styled", fill="#CCC", lw=3, fontsize=12)
        plt.close(fig)


class TestProcessDrawDiamond:
    """Test draw_diamond helper."""

    def test_with_text(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            draw_diamond,
        )

        fig, ax = plt.subplots()
        draw_diamond(ax, 5, 5, 3, "XOR")
        plt.close(fig)

    def test_without_text(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            draw_diamond,
        )

        fig, ax = plt.subplots()
        draw_diamond(ax, 5, 5, 3)
        plt.close(fig)

    def test_custom_fill(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_process_diagrams import (
            draw_diamond,
        )

        fig, ax = plt.subplots()
        draw_diamond(ax, 5, 5, 3, "Y", fill="#EEE", fontsize=12)
        plt.close(fig)


# ── _process_bpmn_uml ─────────────────────────────────────────────────


class TestBPMN:
    """Test generate_bpmn and its sub-helpers."""

    def test_generate_bpmn(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
            generate_bpmn,
        )

        generate_bpmn()

    def test_draw_bpmn_pool_and_lanes(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
            _draw_bpmn_pool_and_lanes,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 110)
        ax.set_ylim(0, 75)
        result = _draw_bpmn_pool_and_lanes(ax)
        assert len(result) == 4
        plt.close(fig)

    def test_draw_bpmn_elements(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
            _draw_bpmn_elements,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 110)
        ax.set_ylim(0, 75)
        _draw_bpmn_elements(ax, 60, 40, 20, 12)
        plt.close(fig)

    def test_draw_bpmn_legend(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
            _draw_bpmn_legend,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 110)
        ax.set_ylim(0, 75)
        _draw_bpmn_legend(ax)
        plt.close(fig)


class TestUMLActivity:
    """Test generate_uml_activity and its sub-helpers."""

    def test_generate_uml_activity(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
            generate_uml_activity,
        )

        generate_uml_activity()

    def test_draw_uml_elements(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
            _draw_uml_elements,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        _draw_uml_elements(ax)
        plt.close(fig)

    def test_draw_uml_legend(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_bpmn_uml import (
            _draw_uml_legend,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        _draw_uml_legend(ax)
        plt.close(fig)


# ── _process_epc_fc ────────────────────────────────────────────────────


class TestEPC:
    """Test generate_epc and its sub-helpers."""

    def test_generate_epc(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
            generate_epc,
        )

        generate_epc()

    def test_draw_epc_event(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
            _draw_epc_event,
        )

        fig, ax = plt.subplots()
        _draw_epc_event(ax, 50, 50, "test event")
        plt.close(fig)

    def test_draw_epc_function(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
            _draw_epc_function,
        )

        fig, ax = plt.subplots()
        _draw_epc_function(ax, 50, 50, "test function")
        plt.close(fig)

    def test_draw_epc_connector(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
            _draw_epc_connector,
        )

        fig, ax = plt.subplots()
        _draw_epc_connector(ax, 50, 50, "XOR")
        plt.close(fig)

    def test_draw_epc_flow(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
            _draw_epc_flow,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 120)
        cx, split_y, step = _draw_epc_flow(ax)
        assert isinstance(cx, int | float)
        assert isinstance(split_y, int | float)
        assert isinstance(step, float)
        plt.close(fig)

    def test_draw_epc_branches(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
            _draw_epc_branches,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 120)
        _draw_epc_branches(ax, 50, 60, 9.5)
        plt.close(fig)

    def test_draw_epc_legend(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_epc_fc import (
            _draw_epc_legend,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 120)
        _draw_epc_legend(ax)
        plt.close(fig)


# ── _process_fc ────────────────────────────────────────────────────────


class TestFlowchart:
    """Test generate_flowchart and its sub-helpers."""

    def test_generate_flowchart(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_fc import (
            generate_flowchart,
        )

        generate_flowchart()

    def test_draw_fc_terminal(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_fc import (
            _draw_fc_terminal,
        )

        fig, ax = plt.subplots()
        _draw_fc_terminal(ax, 50, 50, "START")
        plt.close(fig)

    def test_draw_fc_process_box(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_fc import (
            _draw_fc_process_box,
        )

        fig, ax = plt.subplots()
        _draw_fc_process_box(ax, 50, 50, "Process")
        plt.close(fig)

    def test_draw_fc_io_shape(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_fc import (
            _draw_fc_io_shape,
        )

        fig, ax = plt.subplots()
        _draw_fc_io_shape(ax, 50, 50, "I/O")
        plt.close(fig)

    def test_draw_fc_elements(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_fc import (
            _draw_fc_elements,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 110)
        _draw_fc_elements(ax)
        plt.close(fig)

    def test_draw_fc_legend(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._process_fc import (
            _draw_fc_legend,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 110)
        _draw_fc_legend(ax)
        plt.close(fig)

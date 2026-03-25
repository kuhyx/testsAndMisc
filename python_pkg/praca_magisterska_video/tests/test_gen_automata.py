"""Tests for automata diagram modules (GROUP 3).

Covers:
  - _automata_common.py (helpers, dataclasses)
  - _automata_fa.py (FA recognition diagram)
  - _automata_lba.py (LBA recognition diagram)
  - _automata_pda.py (PDA recognition diagram)
  - _automata_tm.py (TM recognition diagram)
  - generate_automata_diagrams.py (entry module)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

from python_pkg.praca_magisterska_video.generate_images import (
    generate_automata_diagrams as _auto_diags,
)
from python_pkg.praca_magisterska_video.generate_images._automata_common import (
    BG,
    DPI,
    FS,
    FS_SMALL,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    INNER_RATIO,
    LIGHT_BLUE,
    LIGHT_GREEN,
    LIGHT_RED,
    LIGHT_YELLOW,
    LN,
    OUTPUT_DIR,
    ArrowStyle,
    LoopStyle,
    StateStyle,
    draw_curved_arrow,
    draw_self_loop,
    draw_state_circle,
)
from python_pkg.praca_magisterska_video.generate_images._automata_fa import (
    draw_fa_recognition,
)
from python_pkg.praca_magisterska_video.generate_images._automata_lba import (
    draw_lba_recognition,
)
from python_pkg.praca_magisterska_video.generate_images._automata_pda import (
    draw_pda_recognition,
)
from python_pkg.praca_magisterska_video.generate_images._automata_tm import (
    draw_tm_recognition,
)

pytestmark = pytest.mark.usefixtures("_no_savefig")


# ── _automata_common helpers ───────────────────────────────────────────


class TestAutomataCommon:
    """Test draw_state_circle, draw_curved_arrow, draw_self_loop."""

    def test_state_circle_basic(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_state_circle(ax, (0, 0), 0.3, "q0")
        plt.close(fig)

    def test_state_circle_accepting(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_state_circle(ax, (0, 0), 0.3, "q1", StateStyle(accepting=True))
        plt.close(fig)

    def test_state_circle_initial(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_state_circle(ax, (0, 0), 0.3, "q0", StateStyle(initial=True))
        plt.close(fig)

    def test_state_circle_both(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_state_circle(
            ax, (0, 0), 0.3, "q", StateStyle(accepting=True, initial=True)
        )
        plt.close(fig)

    def test_curved_arrow(self) -> None:
        fig, ax = plt.subplots()
        draw_curved_arrow(ax, (0, 0), (1, 1), "a")
        plt.close(fig)

    def test_self_loop_top(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_self_loop(ax, (0, 0), 0.3, "a", LoopStyle(direction="top"))
        plt.close(fig)

    def test_self_loop_bottom(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_self_loop(ax, (0, 0), 0.3, "b", LoopStyle(direction="bottom"))
        plt.close(fig)

    def test_self_loop_default(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_self_loop(ax, (0, 0), 0.3, "c")
        plt.close(fig)

    def test_self_loop_unknown_direction(self) -> None:
        """Cover implicit else when direction is not top/bottom."""
        fig, ax = plt.subplots()
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        draw_self_loop(ax, (0, 0), 0.3, "x", LoopStyle(direction="left"))
        plt.close(fig)

    def test_dataclass_defaults(self) -> None:
        ss = StateStyle()
        assert ss.accepting is False
        assert ss.initial is False
        a = ArrowStyle()
        assert a.fontsize > 0
        ls = LoopStyle()
        assert ls.direction == "top"

    def test_module_constants(self) -> None:
        assert DPI == 300
        assert BG == "white"
        assert isinstance(FS, int | float)
        assert isinstance(FS_SMALL, int | float)
        assert isinstance(FS_TITLE, int | float)
        assert isinstance(INNER_RATIO, float)
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(GRAY5, str)
        assert isinstance(LIGHT_GREEN, str)
        assert isinstance(LIGHT_RED, str)
        assert isinstance(LIGHT_BLUE, str)
        assert isinstance(LIGHT_YELLOW, str)
        assert isinstance(LN, str)
        assert isinstance(OUTPUT_DIR, str)


# ── Diagram functions ──────────────────────────────────────────────────


class TestAutomataDiagrams:
    """Test all recognition diagram functions."""

    def test_fa_recognition(self) -> None:
        draw_fa_recognition()

    def test_pda_recognition(self) -> None:
        draw_pda_recognition()

    def test_lba_recognition(self) -> None:
        draw_lba_recognition()

    def test_tm_recognition(self) -> None:
        draw_tm_recognition()


# ── Entry module ───────────────────────────────────────────────────────


class TestAutomataEntry:
    """Verify generate_automata_diagrams exports are accessible."""

    def test_all_exports(self) -> None:
        assert hasattr(_auto_diags, "__all__")
        for name in _auto_diags.__all__:
            assert hasattr(_auto_diags, name)

    def test_output_dir(self) -> None:
        assert isinstance(_auto_diags.OUTPUT_DIR, str)

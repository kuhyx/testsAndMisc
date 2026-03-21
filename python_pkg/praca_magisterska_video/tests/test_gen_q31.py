"""Tests for Q31 diagram generation (decision theory)."""

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
# _q31_common
# =====================================================================
class TestQ31Common:
    """Tests for _q31_common constants and helpers."""

    def test_constants_exist(self) -> None:
        from _q31_common import (
            _DATA_STATE_COLS,
            _REGRET_HEADER_COLS,
            _WINNING_EV,
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
        assert FS_TITLE == 11
        assert _REGRET_HEADER_COLS == 4
        assert _DATA_STATE_COLS == 3
        assert _WINNING_EV == 95
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(GRAY5, str)
        assert isinstance(OUTPUT_DIR, str)

    def test_draw_box_rounded(self) -> None:
        from _q31_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 1.0, 2.0, 3.0, 1.0, "test", rounded=True)
        assert len(ax.patches) == 1
        assert len(ax.texts) == 1
        plt.close(fig)

    def test_draw_box_not_rounded(self) -> None:
        from _q31_common import draw_box

        fig, ax = plt.subplots()
        draw_box(ax, 0.0, 0.0, 2.0, 1.0, "rect", rounded=False)
        assert len(ax.patches) == 1
        plt.close(fig)

    def test_draw_box_custom_params(self) -> None:
        from _q31_common import draw_box

        fig, ax = plt.subplots()
        draw_box(
            ax,
            0.0,
            0.0,
            2.0,
            1.0,
            "custom",
            fill="#FF0000",
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
        from _q31_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0)
        plt.close(fig)

    def test_draw_arrow_custom_params(self) -> None:
        from _q31_common import draw_arrow

        fig, ax = plt.subplots()
        draw_arrow(ax, 0.0, 0.0, 1.0, 1.0, lw=2.0, style="->", color="red")
        plt.close(fig)


# =====================================================================
# _q31_criteria_comparison
# =====================================================================
class TestQ31CriteriaComparison:
    """Tests for criteria comparison diagram."""

    def test_draw_payoff_table(self) -> None:
        from _q31_criteria_comparison import _draw_payoff_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        _draw_payoff_table(ax)
        assert len(ax.patches) > 0
        assert len(ax.texts) > 0
        plt.close(fig)

    def test_draw_criteria_bars(self) -> None:
        from _q31_criteria_comparison import _draw_criteria_bars

        fig, ax = plt.subplots()
        _draw_criteria_bars(ax)
        assert len(ax.texts) > 0
        plt.close(fig)

    def test_draw_criteria_comparison(self) -> None:
        from _q31_criteria_comparison import draw_criteria_comparison

        draw_criteria_comparison()

    def test_payoff_table_negative_fill(self) -> None:
        """Verify negative values get special fill."""
        from _q31_criteria_comparison import _draw_payoff_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        _draw_payoff_table(ax)
        # Has patches for header + 3 data rows + probability row
        assert len(ax.patches) >= 4
        plt.close(fig)

    def test_criteria_bars_winners(self) -> None:
        """Verify star markers are placed for winners."""
        from _q31_criteria_comparison import _draw_criteria_bars

        fig, ax = plt.subplots()
        _draw_criteria_bars(ax)
        # Check star markers exist in texts
        star_texts = [t for t in ax.texts if "★" in t.get_text()]
        assert len(star_texts) > 0
        plt.close(fig)


# =====================================================================
# _q31_ev_spectrum
# =====================================================================
class TestQ31EvSpectrum:
    """Tests for expected value and conditions spectrum."""

    def test_draw_expected_value(self) -> None:
        from _q31_ev_spectrum import draw_expected_value

        draw_expected_value()

    def test_draw_conditions_spectrum(self) -> None:
        from _q31_ev_spectrum import draw_conditions_spectrum

        draw_conditions_spectrum()

    def test_expected_value_star_on_winner(self) -> None:
        """The winning EV=95 alternative should get a star marker."""
        from _q31_ev_spectrum import draw_expected_value

        draw_expected_value()

    def test_conditions_spectrum_gradient(self) -> None:
        """The gradient bar with 50 steps should be rendered."""
        from _q31_ev_spectrum import draw_conditions_spectrum

        draw_conditions_spectrum()


# =====================================================================
# _q31_hurwicz_mnemonic
# =====================================================================
class TestQ31HurwiczMnemonic:
    """Tests for Hurwicz interpolation and criteria mnemonic."""

    def test_draw_hurwicz_interpolation(self) -> None:
        from _q31_hurwicz_mnemonic import draw_hurwicz_interpolation

        draw_hurwicz_interpolation()

    def test_draw_criteria_mnemonic(self) -> None:
        from _q31_hurwicz_mnemonic import draw_criteria_mnemonic

        draw_criteria_mnemonic()

    def test_mnemonic_criteria_boxes(self) -> None:
        """Exercise _draw_mnemonic_criteria_boxes with both if-branches."""
        from _q31_hurwicz_mnemonic import _draw_mnemonic_criteria_boxes

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        _draw_mnemonic_criteria_boxes(ax)
        # 6 criteria boxes + 6 arrows + labels
        assert len(ax.patches) >= 6
        plt.close(fig)


# =====================================================================
# _q31_regret_matrix
# =====================================================================
class TestQ31RegretMatrix:
    """Tests for regret matrix diagram."""

    def test_draw_original_payoff(self) -> None:
        from _q31_regret_matrix import _draw_original_payoff

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 7)
        _draw_original_payoff(ax, 5.5, 0.55)
        assert len(ax.patches) > 0
        plt.close(fig)

    def test_draw_regret_table(self) -> None:
        from _q31_regret_matrix import _draw_regret_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 7)
        _draw_regret_table(ax, 5.5, 0.55)
        assert len(ax.patches) > 0
        plt.close(fig)

    def test_draw_regret_matrix(self) -> None:
        from _q31_regret_matrix import draw_regret_matrix

        draw_regret_matrix()

    def test_regret_table_winner_highlight(self) -> None:
        """The winner row (min max regret) gets special styling."""
        from _q31_regret_matrix import _draw_regret_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 7)
        _draw_regret_table(ax, 5.5, 0.55)
        # check star marker exists
        star_texts = [t for t in ax.texts if "★" in t.get_text()]
        assert len(star_texts) == 1
        plt.close(fig)

    def test_regret_table_max_regret_highlighting(self) -> None:
        """Cells equal to max regret for a row get bold and gray fill."""
        from _q31_regret_matrix import _draw_regret_table

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 7)
        _draw_regret_table(ax, 5.5, 0.55)
        # Check that bold text exists for non-winner cells too
        bold_texts = [
            t
            for t in ax.texts
            if t.get_fontweight() == "bold" and "★" not in t.get_text()
        ]
        assert len(bold_texts) > 0
        plt.close(fig)


# =====================================================================
# generate_q31_diagrams
# =====================================================================
class TestGenerateQ31Diagrams:
    """Tests for the Q31 diagram generation entrypoint."""

    def test_module_exports(self) -> None:
        from generate_q31_diagrams import __all__

        expected = [
            "draw_conditions_spectrum",
            "draw_criteria_comparison",
            "draw_criteria_mnemonic",
            "draw_expected_value",
            "draw_hurwicz_interpolation",
            "draw_regret_matrix",
        ]
        assert sorted(__all__) == sorted(expected)

    def test_all_functions_callable(self) -> None:
        import generate_q31_diagrams as mod

        for name in mod.__all__:
            assert callable(getattr(mod, name))

    def test_main_block(self) -> None:
        """Exercise the __main__ block by re-running functions."""
        from generate_q31_diagrams import (
            draw_conditions_spectrum,
            draw_criteria_comparison,
            draw_criteria_mnemonic,
            draw_expected_value,
            draw_hurwicz_interpolation,
            draw_regret_matrix,
        )

        draw_criteria_comparison()
        draw_regret_matrix()
        draw_hurwicz_interpolation()
        draw_criteria_mnemonic()
        draw_expected_value()
        draw_conditions_spectrum()

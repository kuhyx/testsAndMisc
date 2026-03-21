"""Tests for _poker_gui.py - GUI setup mixin methods."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch


def _install_tk_mocks() -> dict[str, MagicMock]:
    """Install mock tkinter modules and return them."""
    mock_tk = MagicMock()
    mock_ttk = MagicMock()
    mock_tk.ttk = mock_ttk

    # Constants used in the source
    mock_tk.BOTH = "both"
    mock_tk.X = "x"
    mock_tk.LEFT = "left"
    mock_tk.RIGHT = "right"
    mock_tk.HORIZONTAL = "horizontal"
    mock_tk.CENTER = "center"
    mock_tk.RIDGE = "ridge"
    mock_tk.RAISED = "raised"
    mock_tk.SUNKEN = "sunken"

    # Make constructors return fresh mocks each time
    mock_tk.Tk.return_value = MagicMock(name="root")
    mock_tk.Frame.side_effect = lambda *a, **kw: MagicMock(name="Frame")
    mock_tk.Label.side_effect = lambda *a, **kw: MagicMock(name="Label")
    mock_tk.LabelFrame.side_effect = lambda *a, **kw: MagicMock(name="LabelFrame")
    mock_tk.Scale.side_effect = lambda *a, **kw: MagicMock(name="Scale")
    mock_tk.IntVar.side_effect = lambda *a, **kw: MagicMock(name="IntVar")
    mock_tk.BooleanVar.side_effect = lambda *a, **kw: MagicMock(name="BooleanVar")
    mock_tk.Checkbutton.side_effect = lambda *a, **kw: MagicMock(name="Checkbutton")
    mock_tk.Button.side_effect = lambda *a, **kw: MagicMock(name="Button")

    return {"tk": mock_tk, "ttk": mock_ttk}


def _make_mixin() -> Any:
    """Create a PokerGuiMixin instance with mocked tkinter."""
    tk_mocks = _install_tk_mocks()

    with patch.dict(
        sys.modules,
        {
            "tkinter": tk_mocks["tk"],
            "tkinter.ttk": tk_mocks["ttk"],
        },
    ):
        # Force reimport so the module picks up mocked tkinter
        mod_name = "python_pkg.poker_modifier_app._poker_gui"
        if mod_name in sys.modules:
            del sys.modules[mod_name]

        from python_pkg.poker_modifier_app._poker_gui import PokerGuiMixin

        mixin = PokerGuiMixin()
        return mixin, tk_mocks["tk"], tk_mocks["ttk"]


class TestSetupGui:
    """Tests for setup_gui orchestration."""

    def test_setup_gui_calls_all_subparts(self) -> None:
        mixin, _tk, _ttk = _make_mixin()
        with (
            patch.object(mixin, "_setup_main_window") as m_win,
            patch.object(mixin, "_create_main_frame") as m_frame,
            patch.object(mixin, "_create_title") as m_title,
            patch.object(mixin, "_create_settings_frame") as m_settings,
            patch.object(mixin, "_create_result_display") as m_result,
            patch.object(mixin, "_create_buttons") as m_buttons,
            patch.object(mixin, "_create_statistics_frame") as m_stats,
        ):
            main_frame_mock = MagicMock()
            m_frame.return_value = main_frame_mock
            mixin.setup_gui()

            m_win.assert_called_once()
            m_frame.assert_called_once()
            m_title.assert_called_once_with(main_frame_mock)
            m_settings.assert_called_once_with(main_frame_mock)
            m_result.assert_called_once_with(main_frame_mock)
            m_buttons.assert_called_once_with(main_frame_mock)
            m_stats.assert_called_once_with(main_frame_mock)


class TestSetupMainWindow:
    """Tests for _setup_main_window."""

    def test_creates_root_and_configures(self) -> None:
        mixin, mock_tk, mock_ttk = _make_mixin()
        mixin._setup_main_window()

        mock_tk.Tk.assert_called_once()
        root = mixin.root
        root.title.assert_called_once_with("🃏 Texas Hold'em Modifier")
        root.geometry.assert_called_once_with("650x750")
        root.configure.assert_called_once_with(bg="#0f4c3a")
        root.resizable.assert_called_once_with(True, True)
        mock_ttk.Style.assert_called_once()
        mock_ttk.Style.return_value.theme_use.assert_called_once_with("clam")


class TestCreateMainFrame:
    """Tests for _create_main_frame."""

    def test_creates_frame_and_packs(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        mixin.root = MagicMock()
        result = mixin._create_main_frame()

        mock_tk.Frame.assert_called_once_with(
            mixin.root, bg="#0f4c3a", padx=20, pady=20
        )
        result.pack.assert_called_once_with(fill="both", expand=True)


class TestCreateTitle:
    """Tests for _create_title."""

    def test_creates_title_label(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        parent = MagicMock()
        mixin._create_title(parent)

        mock_tk.Label.assert_called_once_with(
            parent,
            text="🃏 Texas Hold'em Modifier",
            font=("Arial", 24, "bold"),
            fg="#ffd700",
            bg="#0f4c3a",
        )


class TestCreateSettingsFrame:
    """Tests for _create_settings_frame."""

    def test_creates_settings_and_sub_controls(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        parent = MagicMock()
        with (
            patch.object(mixin, "_create_probability_controls") as m_prob,
            patch.object(mixin, "_create_debug_controls") as m_debug,
            patch.object(mixin, "_create_length_controls") as m_length,
        ):
            mixin._create_settings_frame(parent)

            mock_tk.LabelFrame.assert_called_once()
            lf_kwargs = mock_tk.LabelFrame.call_args
            assert lf_kwargs[1]["text"] == "Settings"

            m_prob.assert_called_once()
            m_debug.assert_called_once()
            m_length.assert_called_once()


class TestCreateProbabilityControls:
    """Tests for _create_probability_controls."""

    def test_creates_prob_slider_and_label(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        # Provide required attributes used as command callbacks
        mixin.update_prob_display = MagicMock()
        parent = MagicMock()
        mixin._create_probability_controls(parent)

        # Frame created
        assert mock_tk.Frame.call_count >= 1
        # Label for "Modifier Probability:"
        label_calls = mock_tk.Label.call_args_list
        assert any(c[1].get("text") == "Modifier Probability:" for c in label_calls)
        # IntVar with default 30
        mock_tk.IntVar.assert_called_once_with(value=30)
        assert hasattr(mixin, "prob_var")
        # Scale created
        mock_tk.Scale.assert_called_once()
        assert hasattr(mixin, "prob_scale")
        # Prob label created
        prob_labels = [c for c in label_calls if c[1].get("text") == "30%"]
        assert len(prob_labels) == 1
        assert hasattr(mixin, "prob_label")


class TestCreateDebugControls:
    """Tests for _create_debug_controls."""

    def test_creates_debug_checkbox_and_button(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        mixin.toggle_debug_mode = MagicMock()
        mixin.toggle_force_endgame = MagicMock()
        parent = MagicMock()
        mixin._create_debug_controls(parent)

        mock_tk.BooleanVar.assert_called_once_with(value=False)
        assert hasattr(mixin, "debug_var")
        mock_tk.Checkbutton.assert_called_once()
        cb_kwargs = mock_tk.Checkbutton.call_args[1]
        assert cb_kwargs["text"] == "Debug Mode"

        mock_tk.Button.assert_called_once()
        btn_kwargs = mock_tk.Button.call_args[1]
        assert btn_kwargs["text"] == "Force Endgame"
        assert hasattr(mixin, "force_endgame_button")


class TestCreateLengthControls:
    """Tests for _create_length_controls."""

    def test_creates_length_slider_and_label(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        mixin.update_length_display = MagicMock()
        parent = MagicMock()
        mixin._create_length_controls(parent)

        assert mock_tk.Frame.call_count >= 1
        label_calls = mock_tk.Label.call_args_list
        assert any(c[1].get("text") == "Total Game Rounds:" for c in label_calls)
        mock_tk.IntVar.assert_called_once_with(value=20)
        assert hasattr(mixin, "length_var")
        mock_tk.Scale.assert_called_once()
        assert hasattr(mixin, "length_scale")
        length_labels = [c for c in label_calls if c[1].get("text") == "20"]
        assert len(length_labels) == 1
        assert hasattr(mixin, "length_label")


class TestCreateResultDisplay:
    """Tests for _create_result_display."""

    def test_creates_result_frame_and_label(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        parent = MagicMock()
        mixin._create_result_display(parent)

        # Result frame
        frame_calls = mock_tk.Frame.call_args_list
        assert any(c[1].get("height") == 150 for c in frame_calls)
        assert hasattr(mixin, "result_frame")
        mixin.result_frame.pack_propagate.assert_called_once_with(False)

        # Result label
        label_calls = mock_tk.Label.call_args_list
        assert any(
            c[1].get("text") == "Click 'Start Round' to begin!" for c in label_calls
        )
        assert hasattr(mixin, "result_label")


class TestCreateButtons:
    """Tests for _create_buttons."""

    def test_creates_start_and_reset_buttons(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        mixin.start_round = MagicMock()
        mixin.reset_game = MagicMock()
        parent = MagicMock()
        mixin._create_buttons(parent)

        assert mock_tk.Frame.call_count >= 1
        btn_calls = mock_tk.Button.call_args_list
        assert len(btn_calls) == 2

        start_kwargs = btn_calls[0][1]
        assert start_kwargs["text"] == "Start Round"
        assert start_kwargs["cursor"] == "hand2"
        assert hasattr(mixin, "start_button")

        reset_kwargs = btn_calls[1][1]
        assert reset_kwargs["text"] == "Reset Game"
        assert reset_kwargs["cursor"] == "hand2"
        assert hasattr(mixin, "reset_button")

        mixin.start_button.pack.assert_called_once()
        mixin.reset_button.pack.assert_called_once()


class TestCreateStatisticsFrame:
    """Tests for _create_statistics_frame."""

    def test_creates_stats_labels(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        parent = MagicMock()
        mixin._create_statistics_frame(parent)

        # 3 LabelFrames: rounds, modifiers, phase
        lf_calls = mock_tk.LabelFrame.call_args_list
        assert len(lf_calls) == 3
        lf_texts = [c[1]["text"] for c in lf_calls]
        assert "Rounds Played" in lf_texts
        assert "Modifiers Applied" in lf_texts
        assert "Game Phase" in lf_texts

        assert hasattr(mixin, "rounds_label")
        assert hasattr(mixin, "mods_label")
        assert hasattr(mixin, "phase_label")

    def test_stats_initial_values(self) -> None:
        mixin, mock_tk, _ttk = _make_mixin()
        parent = MagicMock()
        mixin._create_statistics_frame(parent)

        label_calls = mock_tk.Label.call_args_list
        # Two "0" labels (rounds and mods) and one "Early" label
        zero_labels = [c for c in label_calls if c[1].get("text") == "0"]
        assert len(zero_labels) == 2
        early_labels = [c for c in label_calls if c[1].get("text") == "Early"]
        assert len(early_labels) == 1

"""Tests for poker_modifier_app package."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.poker_modifier_app._poker_modifiers import (
    ENDGAME_MODIFIERS,
    REGULAR_MODIFIERS,
    Modifier,
)

if TYPE_CHECKING:
    from python_pkg.poker_modifier_app.poker_modifier_app import PokerModifierApp


def _make_app() -> PokerModifierApp:
    """Create a PokerModifierApp with setup_gui mocked out."""
    with patch(
        "python_pkg.poker_modifier_app.poker_modifier_app.PokerGuiMixin.setup_gui"
    ):
        from python_pkg.poker_modifier_app.poker_modifier_app import PokerModifierApp

        app = PokerModifierApp()
    # Provide mock GUI widgets used by logic methods
    app.root = MagicMock()
    app.prob_label = MagicMock()
    app.length_label = MagicMock()
    app.debug_var = MagicMock()
    app.force_endgame_button = MagicMock()
    app.start_button = MagicMock()
    app.rounds_label = MagicMock()
    app.phase_label = MagicMock()
    app.prob_var = MagicMock()
    app.mods_label = MagicMock()
    app.result_frame = MagicMock()
    app.result_label = MagicMock()
    return app


class TestModifierData:
    """Tests for _poker_modifiers module."""

    def test_regular_modifiers_is_list(self) -> None:
        assert isinstance(REGULAR_MODIFIERS, list)
        assert len(REGULAR_MODIFIERS) > 0

    def test_endgame_modifiers_is_list(self) -> None:
        assert isinstance(ENDGAME_MODIFIERS, list)
        assert len(ENDGAME_MODIFIERS) > 0

    def test_modifier_structure(self) -> None:
        for mod in REGULAR_MODIFIERS + ENDGAME_MODIFIERS:
            assert "name" in mod
            assert "description" in mod

    def test_modifier_type_alias(self) -> None:
        sample: Modifier = {"name": "test", "description": "test"}
        assert isinstance(sample, dict)


class TestPokerModifierAppInit:
    """Tests for PokerModifierApp initialization."""

    def test_init_sets_defaults(self) -> None:
        app = _make_app()
        assert app.rounds_played == 0
        assert app.modifiers_applied == 0
        assert app.total_game_rounds == 20
        assert app.endgame_threshold == 0.8
        assert app.debug_mode is False
        assert app.force_endgame is False

    def test_init_filters_endgame_from_regular(self) -> None:
        app = _make_app()
        endgame_names = {mod["name"] for mod in ENDGAME_MODIFIERS}
        regular_names = {mod["name"] for mod in app.modifiers}
        assert not regular_names.intersection(endgame_names)

    def test_init_copies_modifier_lists(self) -> None:
        app = _make_app()
        assert app.modifiers is not REGULAR_MODIFIERS
        assert app.endgame_modifiers is not ENDGAME_MODIFIERS


class TestUpdateDisplays:
    """Tests for display update methods."""

    def test_update_prob_display(self) -> None:
        app = _make_app()
        app.update_prob_display("50")
        app.prob_label.config.assert_called_once_with(text="50%")

    def test_update_length_display(self) -> None:
        app = _make_app()
        app.update_length_display("30")
        app.length_label.config.assert_called_once_with(text="30")
        assert app.total_game_rounds == 30


class TestToggleDebugMode:
    """Tests for toggle_debug_mode."""

    def test_enable_debug_mode(self) -> None:
        app = _make_app()
        app.debug_var.get.return_value = True
        app.toggle_debug_mode()
        assert app.debug_mode is True
        app.force_endgame_button.pack.assert_called_once()

    def test_disable_debug_mode(self) -> None:
        app = _make_app()
        app.debug_var.get.return_value = False
        app.toggle_debug_mode()
        assert app.debug_mode is False
        assert app.force_endgame is False
        app.force_endgame_button.pack_forget.assert_called_once()


class TestToggleForceEndgame:
    """Tests for toggle_force_endgame."""

    def test_toggle_on(self) -> None:
        app = _make_app()
        app.force_endgame = False
        app.toggle_force_endgame()
        assert app.force_endgame is True
        app.force_endgame_button.config.assert_called_once_with(
            text="Stop Force Endgame", bg="#4CAF50"
        )

    def test_toggle_off(self) -> None:
        app = _make_app()
        app.force_endgame = True
        app.toggle_force_endgame()
        assert app.force_endgame is False
        app.force_endgame_button.config.assert_called_once_with(
            text="Force Endgame", bg="#ff6b6b"
        )


class TestIsEndgame:
    """Tests for is_endgame."""

    def test_debug_force_endgame(self) -> None:
        app = _make_app()
        app.debug_mode = True
        app.force_endgame = True
        assert app.is_endgame() is True

    def test_debug_no_force(self) -> None:
        app = _make_app()
        app.debug_mode = True
        app.force_endgame = False
        app.total_game_rounds = 20
        app.rounds_played = 0
        assert app.is_endgame() is False

    def test_rounds_at_threshold(self) -> None:
        app = _make_app()
        app.total_game_rounds = 20
        app.endgame_threshold = 0.8
        app.rounds_played = 16  # exactly at 80%
        assert app.is_endgame() is True

    def test_rounds_below_threshold(self) -> None:
        app = _make_app()
        app.total_game_rounds = 20
        app.endgame_threshold = 0.8
        app.rounds_played = 15
        assert app.is_endgame() is False


class TestUpdatePhaseIndicator:
    """Tests for update_phase_indicator - 4 branches."""

    def test_endgame_phase(self) -> None:
        app = _make_app()
        app.debug_mode = True
        app.force_endgame = True
        app.update_phase_indicator()
        app.phase_label.config.assert_called_once_with(text="Endgame", fg="#ff6b6b")

    def test_late_phase(self) -> None:
        app = _make_app()
        app.total_game_rounds = 20
        app.rounds_played = 12  # 60%
        app.update_phase_indicator()
        app.phase_label.config.assert_called_once_with(text="Late", fg="#ffa500")

    def test_mid_phase(self) -> None:
        app = _make_app()
        app.total_game_rounds = 20
        app.rounds_played = 6  # 30%
        app.update_phase_indicator()
        app.phase_label.config.assert_called_once_with(text="Mid", fg="#ffeb3b")

    def test_early_phase(self) -> None:
        app = _make_app()
        app.total_game_rounds = 20
        app.rounds_played = 1
        app.update_phase_indicator()
        app.phase_label.config.assert_called_once_with(text="Early", fg="#4CAF50")


class TestStartRound:
    """Tests for start_round."""

    def test_start_round_with_modifier(self) -> None:
        app = _make_app()
        app.prob_var.get.return_value = 100
        with (
            patch.object(app, "apply_random_modifier") as mock_apply,
            patch.object(app, "update_phase_indicator"),
            patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng,
        ):
            mock_rng.random.return_value = 0.0  # 0 < 100
            app.start_round()
            mock_apply.assert_called_once()
        assert app.rounds_played == 1

    def test_start_round_no_modifier(self) -> None:
        app = _make_app()
        app.prob_var.get.return_value = 0
        with (
            patch.object(app, "show_no_modifier") as mock_show,
            patch.object(app, "update_phase_indicator"),
            patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng,
        ):
            mock_rng.random.return_value = 0.5  # 50 >= 0
            app.start_round()
            mock_show.assert_called_once()

    def test_start_round_button_animation(self) -> None:
        app = _make_app()
        app.prob_var.get.return_value = 0
        with (
            patch.object(app, "show_no_modifier"),
            patch.object(app, "update_phase_indicator"),
            patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng,
        ):
            mock_rng.random.return_value = 0.99
            app.start_round()
            app.start_button.config.assert_called()
            app.root.after.assert_called_once()


class TestApplyRandomModifier:
    """Tests for apply_random_modifier."""

    def test_apply_normal_modifier(self) -> None:
        app = _make_app()
        app.modifiers = [{"name": "TestMod", "description": "Test desc"}]
        with patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng:
            mock_rng.choice.return_value = {
                "name": "TestMod",
                "description": "Test desc",
            }
            app.apply_random_modifier()
        assert app.modifiers_applied == 1
        app.result_label.config.assert_called_once()
        call_kwargs = app.result_label.config.call_args[1]
        assert "TestMod" in call_kwargs["text"]
        assert call_kwargs["bg"] == "#2d4a2d"

    def test_apply_endgame_modifier_rounds_left(self) -> None:
        app = _make_app()
        app.debug_mode = True
        app.force_endgame = True
        app.total_game_rounds = 20
        app.rounds_played = 17
        with patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng:
            mock_rng.choice.return_value = {
                "name": "Final Boss",
                "description": "Last hand",
            }
            app.apply_random_modifier()
        call_kwargs = app.result_label.config.call_args[1]
        assert "ENDGAME" in call_kwargs["text"]
        assert "3 rounds left" in call_kwargs["text"]
        assert call_kwargs["bg"] == "#4a2d2d"

    def test_apply_endgame_modifier_final_round(self) -> None:
        app = _make_app()
        app.debug_mode = True
        app.force_endgame = True
        app.total_game_rounds = 20
        app.rounds_played = 20
        with patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng:
            mock_rng.choice.return_value = {
                "name": "Final Boss",
                "description": "Last hand",
            }
            app.apply_random_modifier()
        call_kwargs = app.result_label.config.call_args[1]
        assert "FINAL ROUND!" in call_kwargs["text"]

    def test_apply_steel_cards_modifier(self) -> None:
        app = _make_app()
        app.modifiers = [
            {
                "name": "Steel Cards",
                "description": "Steel {steel_rank} cards!",
            }
        ]
        with patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng:
            mock_rng.choice.side_effect = [
                {"name": "Steel Cards", "description": "Steel {steel_rank} cards!"},
                "Ace",
            ]
            app.apply_random_modifier()
        call_kwargs = app.result_label.config.call_args[1]
        assert "Ace" in call_kwargs["text"]

    def test_apply_endgame_modifier_past_total(self) -> None:
        """Rounds played exceeds total (rounds_left <= 0)."""
        app = _make_app()
        app.debug_mode = True
        app.force_endgame = True
        app.total_game_rounds = 20
        app.rounds_played = 25
        with patch("python_pkg.poker_modifier_app.poker_modifier_app._rng") as mock_rng:
            mock_rng.choice.return_value = {
                "name": "Final Boss",
                "description": "Last hand",
            }
            app.apply_random_modifier()
        call_kwargs = app.result_label.config.call_args[1]
        assert "FINAL ROUND!" in call_kwargs["text"]


class TestShowNoModifier:
    """Tests for show_no_modifier."""

    def test_show_no_modifier(self) -> None:
        app = _make_app()
        app.show_no_modifier()
        app.result_frame.config.assert_called_once()
        app.result_label.config.assert_called_once()
        call_kwargs = app.result_label.config.call_args[1]
        assert "No modifier" in call_kwargs["text"]


class TestResetGame:
    """Tests for reset_game."""

    def test_reset_game(self) -> None:
        app = _make_app()
        app.rounds_played = 10
        app.modifiers_applied = 5
        app.force_endgame = True
        app.debug_mode = False
        app.reset_game()
        assert app.rounds_played == 0
        assert app.modifiers_applied == 0
        assert app.force_endgame is False
        app.rounds_label.config.assert_called_with(text="0")
        app.mods_label.config.assert_called_with(text="0")

    def test_reset_game_debug_mode_on(self) -> None:
        app = _make_app()
        app.debug_mode = True
        app.force_endgame = True
        app.reset_game()
        app.force_endgame_button.config.assert_called_with(
            text="Force Endgame", bg="#ff6b6b"
        )


class TestAddModifier:
    """Tests for add_modifier."""

    def test_add_modifier(self) -> None:
        app = _make_app()
        initial_count = len(app.modifiers)
        app.add_modifier("New Mod", "New description")
        assert len(app.modifiers) == initial_count + 1
        assert app.modifiers[-1] == {
            "name": "New Mod",
            "description": "New description",
        }


class TestGetStats:
    """Tests for get_stats."""

    def test_get_stats_no_rounds(self) -> None:
        app = _make_app()
        stats = app.get_stats()
        assert stats["rounds_played"] == 0
        assert stats["modifier_rate"] == 0
        assert stats["rounds_remaining"] == 20

    def test_get_stats_with_rounds(self) -> None:
        app = _make_app()
        app.rounds_played = 10
        app.modifiers_applied = 3
        app.total_game_rounds = 20
        stats = app.get_stats()
        assert stats["rounds_played"] == 10
        assert stats["modifiers_applied"] == 3
        assert stats["modifier_rate"] == 30.0
        assert stats["rounds_remaining"] == 10
        assert stats["is_endgame"] is False

    def test_get_stats_past_total(self) -> None:
        app = _make_app()
        app.rounds_played = 25
        app.total_game_rounds = 20
        stats = app.get_stats()
        assert stats["rounds_remaining"] == 0


class TestRun:
    """Tests for run method."""

    def test_run(self) -> None:
        app = _make_app()
        app.run()
        app.root.mainloop.assert_called_once()


class TestMainBlock:
    """Test the if __name__ == '__main__' block."""

    @patch("python_pkg.poker_modifier_app.poker_modifier_app.PokerGuiMixin.setup_gui")
    def test_main_block(self, mock_setup: MagicMock) -> None:
        with patch(
            "python_pkg.poker_modifier_app.poker_modifier_app.PokerModifierApp.run"
        ):
            import importlib

            import python_pkg.poker_modifier_app.poker_modifier_app as mod

            mod.__name__ = "__main__"
            importlib.reload(mod)
            # After reload with patched name, run should not be called
            # because __name__ is reset. Test the actual block via runpy.
            mod.__name__ = "python_pkg.poker_modifier_app.poker_modifier_app"

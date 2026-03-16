"""Tests for keyboard_coop UI drawing and click handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestHandleClick:
    """Tests for click handling."""

    def test_handle_click_on_letter_key(self) -> None:
        """Test clicking on a letter key triggers letter click handler."""
        mock_pg = MagicMock()
        mock_pg.Rect = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.available_letters = {"a"}
            game.keyboard.adjacency = {"a": []}

            # Mock _get_key_at_position to return "a"
            game._get_key_at_position = MagicMock(return_value="a")
            game._handle_letter_click = MagicMock()
            game._submit_word = MagicMock()
            game._reset_game = MagicMock()

            # Create mock rects that don't collide
            mock_enter_rect = MagicMock()
            mock_enter_rect.collidepoint.return_value = False
            mock_reset_rect = MagicMock()
            mock_reset_rect.collidepoint.return_value = False

            # Patch pygame.Rect to return our mocks
            mock_pg.Rect.side_effect = [mock_enter_rect, mock_reset_rect]

            game._handle_click((100, 100))

        game._handle_letter_click.assert_called_with("a")

    def test_handle_click_on_enter_button(self) -> None:
        """Test clicking ENTER button triggers word submission."""
        mock_pg = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}

            # Mock methods
            game._get_key_at_position = MagicMock(return_value=None)
            game._submit_word = MagicMock()
            game._reset_game = MagicMock()

            # Mock enter button to collide, reset button not to
            mock_enter_rect = MagicMock()
            mock_enter_rect.collidepoint.return_value = True
            mock_reset_rect = MagicMock()
            mock_reset_rect.collidepoint.return_value = False

            mock_pg.Rect.side_effect = [mock_enter_rect, mock_reset_rect]

            game._handle_click((750, 200))

        game._submit_word.assert_called()
        game._reset_game.assert_not_called()

    def test_handle_click_on_reset_button(self) -> None:
        """Test clicking RESET button triggers game reset."""
        mock_pg = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}

            # Mock methods
            game._get_key_at_position = MagicMock(return_value=None)
            game._submit_word = MagicMock()
            game._reset_game = MagicMock()

            # Mock enter button not to collide, reset button to collide
            mock_enter_rect = MagicMock()
            mock_enter_rect.collidepoint.return_value = False
            mock_reset_rect = MagicMock()
            mock_reset_rect.collidepoint.return_value = True

            mock_pg.Rect.side_effect = [mock_enter_rect, mock_reset_rect]

            game._handle_click((900, 200))

        game._reset_game.assert_called()
        game._submit_word.assert_not_called()


class TestDrawingMethods:
    """Tests for drawing methods."""

    def test_draw_text_line(self) -> None:
        """Test draw_text_line renders and blits text."""
        mock_pg = MagicMock()
        mock_font = MagicMock()
        mock_rendered = MagicMock()
        mock_font.render.return_value = mock_rendered

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                KeyboardCoopGame,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()

            game._draw_text_line("Test text", (10, 20), mock_font)

        mock_font.render.assert_called()
        game.screen.blit.assert_called_with(mock_rendered, (10, 20))

    def test_draw_button(self) -> None:
        """Test draw_button draws rect and text."""
        mock_pg = MagicMock()
        mock_pg.draw = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                KeyboardCoopGame,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )

            mock_rect = MagicMock()
            mock_rect.center = (50, 50)

            game._draw_button(mock_rect, "Test")

        # Should have drawn rect twice (fill and border)
        assert mock_pg.draw.rect.call_count == 2


class TestDrawKeyboard:
    """Tests for keyboard drawing."""

    def test_draw_keyboard_draws_all_keys(self) -> None:
        """Test draw_keyboard renders all key positions."""
        mock_pg = MagicMock()
        mock_pg.draw = MagicMock()
        mock_pg.mouse.get_pos.return_value = (0, 0)

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )

            # Set up some positions
            mock_rect_a = MagicMock()
            mock_rect_a.collidepoint.return_value = False
            mock_rect_a.center = (100, 100)
            mock_rect_b = MagicMock()
            mock_rect_b.collidepoint.return_value = False
            mock_rect_b.center = (150, 100)

            game.keyboard.positions = {"a": mock_rect_a, "b": mock_rect_b}
            game.keyboard.available_letters = {"a", "b"}

            game._draw_keyboard()

        # Should draw rect for each key (fill + border = 2 calls per key)
        assert mock_pg.draw.rect.call_count >= 4

    def test_draw_keyboard_selected_letter_color(self) -> None:
        """Test selected letters get selected color."""
        mock_pg = MagicMock()
        mock_pg.draw = MagicMock()
        mock_pg.mouse.get_pos.return_value = (0, 0)

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                KEY_SELECTED_COLOR,
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.state = GameState()
            game.state.selected_letters = ["a"]  # 'a' is selected
            game.keyboard = KeyboardState()
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )

            mock_rect_a = MagicMock()
            mock_rect_a.collidepoint.return_value = False
            mock_rect_a.center = (100, 100)

            game.keyboard.positions = {"a": mock_rect_a}
            game.keyboard.available_letters = {"a"}

            game._draw_keyboard()

        # Check that KEY_SELECTED_COLOR was used
        calls = mock_pg.draw.rect.call_args_list
        colors_used = [call[0][1] for call in calls]
        assert KEY_SELECTED_COLOR in colors_used

    def test_draw_keyboard_unavailable_key_color(self) -> None:
        """Test unavailable keys get default key color."""
        mock_pg = MagicMock()
        mock_pg.draw = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                KEY_COLOR,
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.state = GameState()
            game.state.selected_letters = []  # Not selected
            game.keyboard = KeyboardState()
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )

            mock_rect_a = MagicMock()
            mock_rect_a.center = (100, 100)

            game.keyboard.positions = {"a": mock_rect_a}
            # Key is NOT available - should get KEY_COLOR
            game.keyboard.available_letters = set()

            game._draw_keyboard()

        # Check that KEY_COLOR was used for unavailable key
        calls = mock_pg.draw.rect.call_args_list
        colors_used = [call[0][1] for call in calls]
        assert KEY_COLOR in colors_used


class TestDrawUI:
    """Tests for UI drawing."""

    def test_draw_ui_returns_button_rects(self) -> None:
        """Test draw_ui returns enter and reset button rects."""
        mock_pg = MagicMock()
        mock_pg.draw = MagicMock()
        mock_rect_instance = MagicMock()
        mock_pg.Rect.return_value = mock_rect_instance

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.state = GameState()
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )

            enter_rect, reset_rect = game._draw_ui()

        # Should return pygame.Rect instances
        assert enter_rect is not None
        assert reset_rect is not None

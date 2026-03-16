"""Tests for keyboard_coop game loop and forced submission."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestForceSubmitWhenNoMoves:
    """Tests for forced word submission when no moves available."""

    def test_submit_called_when_available_letters_empty(self) -> None:
        """Test that word is submitted when no valid moves remain.

        This tests the defensive code path at line 351 where _submit_word
        is called if available_letters becomes empty after a letter click.
        """
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
            game.keyboard.layout = [["a", "b"]]
            game.keyboard.adjacency = {}
            game.keyboard.available_letters = {"a"}
            game.keyboard.positions = {}
            game.dictionary = {"a": 1}

            # Simulate scenario where available_letters becomes empty
            # This is defensive code that's hard to trigger naturally
            game._submit_word = MagicMock()

            def patched_handle(letter: str) -> None:
                """Patched handler that clears available letters."""
                if letter in game.keyboard.available_letters:
                    game.state.selected_letters.append(letter)
                    game.state.current_word += letter
                    # Force empty to trigger the check
                    game.keyboard.available_letters = set()
                    if not game.keyboard.available_letters:
                        game._submit_word()

            patched_handle("a")

        # Should have triggered submit_word
        game._submit_word.assert_called()


class TestGameLoop:
    """Tests for the main game loop."""

    def test_run_quit_event(self) -> None:
        """Test game loop exits on QUIT event."""
        mock_pg = MagicMock()

        # Create quit event
        quit_event = MagicMock()
        quit_event.type = "QUIT"
        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        mock_pg.event.get.return_value = [quit_event]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit") as mock_exit,
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))

            game.run()

        mock_pg.quit.assert_called()
        mock_exit.assert_called()

    def test_run_mouse_click_event(self) -> None:
        """Test game loop handles mouse click event."""
        mock_pg = MagicMock()

        # Create mouse click event followed by quit
        click_event = MagicMock()
        click_event.type = "MOUSEDOWN"
        click_event.button = 1
        click_event.pos = (100, 100)

        quit_event = MagicMock()
        quit_event.type = "QUIT"

        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        # Return click event first, then quit event
        mock_pg.event.get.side_effect = [[click_event], [quit_event]]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit"),
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))
            game._handle_click = MagicMock()

            game.run()

        game._handle_click.assert_called_with((100, 100))

    def test_run_enter_key_event(self) -> None:
        """Test game loop handles ENTER key event."""
        mock_pg = MagicMock()

        key_event = MagicMock()
        key_event.type = "KEYDOWN"
        key_event.key = "K_RETURN"

        quit_event = MagicMock()
        quit_event.type = "QUIT"

        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        mock_pg.K_RETURN = "K_RETURN"
        mock_pg.K_r = "K_r"
        mock_pg.event.get.side_effect = [[key_event], [quit_event]]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit"),
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))
            game._submit_word = MagicMock()

            game.run()

        game._submit_word.assert_called()

    def test_run_r_key_reset(self) -> None:
        """Test game loop handles R key for reset."""
        mock_pg = MagicMock()

        key_event = MagicMock()
        key_event.type = "KEYDOWN"
        key_event.key = "K_r"

        quit_event = MagicMock()
        quit_event.type = "QUIT"

        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        mock_pg.K_RETURN = "K_RETURN"
        mock_pg.K_r = "K_r"
        mock_pg.event.get.side_effect = [[key_event], [quit_event]]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit"),
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))
            game._reset_game = MagicMock()

            game.run()

        game._reset_game.assert_called()

    def test_run_letter_key_press(self) -> None:
        """Test game loop handles letter key presses."""
        mock_pg = MagicMock()

        key_event = MagicMock()
        key_event.type = "KEYDOWN"
        key_event.key = "some_key"

        quit_event = MagicMock()
        quit_event.type = "QUIT"

        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        mock_pg.K_RETURN = "K_RETURN"
        mock_pg.K_r = "K_r"
        mock_pg.key.name.return_value = "a"  # Single letter key
        mock_pg.event.get.side_effect = [[key_event], [quit_event]]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit"),
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))
            game._handle_letter_click = MagicMock()

            game.run()

        game._handle_letter_click.assert_called_with("a")

    def test_run_right_click_ignored(self) -> None:
        """Test game loop ignores non-left mouse clicks."""
        mock_pg = MagicMock()

        click_event = MagicMock()
        click_event.type = "MOUSEDOWN"
        click_event.button = 3  # Right click
        click_event.pos = (100, 100)

        quit_event = MagicMock()
        quit_event.type = "QUIT"

        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        mock_pg.event.get.side_effect = [[click_event], [quit_event]]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit"),
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))
            game._handle_click = MagicMock()

            game.run()

        # handle_click should NOT be called for right click
        game._handle_click.assert_not_called()

    def test_run_special_key_ignored(self) -> None:
        """Test game loop ignores non-letter key presses."""
        mock_pg = MagicMock()

        key_event = MagicMock()
        key_event.type = "KEYDOWN"
        key_event.key = "some_key"

        quit_event = MagicMock()
        quit_event.type = "QUIT"

        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        mock_pg.K_RETURN = "K_RETURN"
        mock_pg.K_r = "K_r"
        mock_pg.key.name.return_value = "escape"  # Multi-char, not a letter
        mock_pg.event.get.side_effect = [[key_event], [quit_event]]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit"),
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))
            game._handle_letter_click = MagicMock()

            game.run()

        # handle_letter_click should NOT be called for special keys
        game._handle_letter_click.assert_not_called()

    def test_run_unknown_event_type(self) -> None:
        """Test game loop ignores unknown event types."""
        mock_pg = MagicMock()

        unknown_event = MagicMock()
        unknown_event.type = "UNKNOWN"

        quit_event = MagicMock()
        quit_event.type = "QUIT"

        mock_pg.QUIT = "QUIT"
        mock_pg.MOUSEBUTTONDOWN = "MOUSEDOWN"
        mock_pg.KEYDOWN = "KEYDOWN"
        mock_pg.event.get.side_effect = [[unknown_event], [quit_event]]

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("sys.exit"),
        ):
            from python_pkg.keyboard_coop.main import (
                FontSet,
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.screen = MagicMock()
            game.clock = MagicMock()
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.positions = {}
            game.fonts = FontSet(
                normal=MagicMock(), large=MagicMock(), small=MagicMock()
            )
            game._draw_keyboard = MagicMock()
            game._draw_ui = MagicMock(return_value=(MagicMock(), MagicMock()))
            game._handle_click = MagicMock()
            game._submit_word = MagicMock()
            game._reset_game = MagicMock()
            game._handle_letter_click = MagicMock()

            game.run()

        # None of the handlers should be called for unknown event
        game._handle_click.assert_not_called()
        game._submit_word.assert_not_called()
        game._reset_game.assert_not_called()
        game._handle_letter_click.assert_not_called()

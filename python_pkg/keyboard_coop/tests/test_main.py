"""Unit tests for keyboard_coop module."""

# ruff: noqa: SLF001
# Tests need to access private members to verify internal logic

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from python_pkg.keyboard_coop.main import KeyboardCoopGame


# Need to mock pygame before importing the module
@pytest.fixture(autouse=True)
def mock_pygame() -> MagicMock:
    """Mock pygame to prevent display initialization."""
    with patch.dict("sys.modules", {"pygame": MagicMock()}):
        yield


class TestConstants:
    """Tests for module constants."""

    def test_screen_dimensions(self) -> None:
        """Test screen dimension constants."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import SCREEN_HEIGHT, SCREEN_WIDTH

        expected_width = 1366
        expected_height = 768
        assert expected_width == SCREEN_WIDTH
        assert expected_height == SCREEN_HEIGHT

    def test_min_word_length(self) -> None:
        """Test minimum word length constant."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import MIN_WORD_LENGTH

        expected_min = 3
        assert expected_min == MIN_WORD_LENGTH

    def test_keyboard_layout_structure(self) -> None:
        """Test KEYBOARD_LAYOUT has correct structure."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import KEYBOARD_LAYOUT

        expected_rows = 3
        assert len(KEYBOARD_LAYOUT) == expected_rows
        expected_first_row_len = 10
        expected_second_row_len = 9
        expected_third_row_len = 7
        assert len(KEYBOARD_LAYOUT[0]) == expected_first_row_len
        assert len(KEYBOARD_LAYOUT[1]) == expected_second_row_len
        assert len(KEYBOARD_LAYOUT[2]) == expected_third_row_len


class TestKeyAdjacency:
    """Tests for KEY_ADJACENCY mapping."""

    def test_q_adjacents(self) -> None:
        """Test Q key has correct adjacent keys."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import KEY_ADJACENCY

        assert set(KEY_ADJACENCY["q"]) == {"w", "a", "s"}

    def test_all_letters_have_adjacents(self) -> None:
        """Test all 26 letters have adjacency entries."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import KEY_ADJACENCY

        alphabet = "qwertyuiopasdfghjklzxcvbnm"
        for letter in alphabet:
            assert letter in KEY_ADJACENCY
            assert len(KEY_ADJACENCY[letter]) > 0


class TestGameState:
    """Tests for GameState dataclass."""

    def test_default_values(self) -> None:
        """Test GameState default values."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import GameState

        state = GameState()
        assert state.current_player == 0
        assert state.current_word == ""
        assert state.selected_letters == []
        assert state.score == 0
        assert state.game_over is False
        assert "Player 1" in state.message

    def test_custom_values(self) -> None:
        """Test GameState with custom values."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import GameState

        state = GameState(
            current_player=1,
            current_word="test",
            selected_letters=["t", "e", "s", "t"],
            score=100,
            game_over=True,
            message="Game Over!",
        )
        assert state.current_player == 1
        assert state.current_word == "test"
        expected_score = 100
        assert state.score == expected_score


class TestKeyboardState:
    """Tests for KeyboardState dataclass."""

    def test_default_values(self) -> None:
        """Test KeyboardState default values."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import KeyboardState

        kb_state = KeyboardState()
        assert kb_state.layout == []
        assert kb_state.available_letters == set()
        assert kb_state.adjacency == {}
        assert kb_state.positions == {}


class TestFontSet:
    """Tests for FontSet dataclass."""

    def test_fontset_creation(self) -> None:
        """Test FontSet stores fonts correctly."""
        mock_font = MagicMock()
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import FontSet

        fonts = FontSet(normal=mock_font, large=mock_font, small=mock_font)
        assert fonts.normal == mock_font
        assert fonts.large == mock_font
        assert fonts.small == mock_font


class TestColors:
    """Tests for color constants."""

    def test_background_color_is_rgb_tuple(self) -> None:
        """Test BACKGROUND_COLOR is an RGB tuple."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import BACKGROUND_COLOR

        expected_len = 3
        assert len(BACKGROUND_COLOR) == expected_len
        assert all(isinstance(c, int) for c in BACKGROUND_COLOR)

    def test_player_colors_list(self) -> None:
        """Test PLAYER_COLORS has colors for 2 players."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            from python_pkg.keyboard_coop.main import PLAYER_COLORS

        expected_players = 2
        assert len(PLAYER_COLORS) == expected_players


class TestKeyboardCoopGame:
    """Tests for KeyboardCoopGame class methods."""

    @pytest.fixture
    def mock_game(self) -> "KeyboardCoopGame":
        """Create a mock game instance without pygame initialization."""
        mock_pg = MagicMock()
        mock_pg.font.Font.return_value = MagicMock()
        mock_pg.Rect = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                GameState,
                KeyboardCoopGame,
                KeyboardState,
            )

            # Create game without calling __init__ directly
            game = object.__new__(KeyboardCoopGame)
            game.state = GameState()
            game.keyboard = KeyboardState()
            game.keyboard.layout = [["a", "b", "c"], ["d", "e", "f"]]
            game.keyboard.adjacency = {
                "a": ["b", "d"],
                "b": ["a", "c", "e"],
                "c": ["b", "f"],
                "d": ["a", "e"],
                "e": ["b", "d", "f"],
                "f": ["c", "e"],
            }
            game.keyboard.available_letters = {"a", "b", "c", "d", "e", "f"}
            game.dictionary = {"cat", "bat", "cab", "bad", "bed", "fed", "fad", "ace"}
            return game

    def test_is_valid_move_first_letter(self, mock_game: "KeyboardCoopGame") -> None:
        """Test first letter is always valid."""
        mock_game.state.selected_letters = []
        assert mock_game._is_valid_move("a") is True
        assert mock_game._is_valid_move("z") is True

    def test_is_valid_move_adjacent(self, mock_game: "KeyboardCoopGame") -> None:
        """Test adjacent letter is valid."""
        mock_game.state.selected_letters = ["a"]
        # "b" and "d" are adjacent to "a"
        assert mock_game._is_valid_move("b") is True
        assert mock_game._is_valid_move("d") is True

    def test_is_valid_move_not_adjacent(self, mock_game: "KeyboardCoopGame") -> None:
        """Test non-adjacent letter is invalid."""
        mock_game.state.selected_letters = ["a"]
        # "f" is not adjacent to "a"
        assert mock_game._is_valid_move("f") is False

    def test_is_valid_word_true(self, mock_game: "KeyboardCoopGame") -> None:
        """Test valid word returns True."""
        assert mock_game._is_valid_word("cat") is True
        assert mock_game._is_valid_word("CAT") is True  # Case insensitive

    def test_is_valid_word_false(self, mock_game: "KeyboardCoopGame") -> None:
        """Test invalid word returns False."""
        assert mock_game._is_valid_word("xyz") is False

    def test_calculate_score_min_length(self, mock_game: "KeyboardCoopGame") -> None:
        """Test score calculation for minimum length word."""
        # 3-letter word: 2^(3-2) = 2
        assert mock_game._calculate_score(3) == 2

    def test_calculate_score_longer_word(self, mock_game: "KeyboardCoopGame") -> None:
        """Test score calculation for longer words."""
        # 4-letter: 2^(4-2) = 4
        assert mock_game._calculate_score(4) == 4
        # 5-letter: 2^(5-2) = 8
        assert mock_game._calculate_score(5) == 8

    def test_calculate_score_too_short(self, mock_game: "KeyboardCoopGame") -> None:
        """Test score for words below minimum length is 0."""
        assert mock_game._calculate_score(2) == 0
        assert mock_game._calculate_score(1) == 0

    def test_handle_letter_click_valid(self, mock_game: "KeyboardCoopGame") -> None:
        """Test clicking a valid letter adds it to word."""
        mock_game.state.selected_letters = []
        mock_game.state.current_word = ""
        mock_game.state.current_player = 0

        mock_game._handle_letter_click("a")

        assert mock_game.state.selected_letters == ["a"]
        assert mock_game.state.current_word == "a"
        assert mock_game.state.current_player == 1  # Switched

    def test_handle_letter_click_invalid_not_available(
        self, mock_game: "KeyboardCoopGame"
    ) -> None:
        """Test clicking unavailable letter does nothing."""
        mock_game.keyboard.available_letters = {"b", "c"}
        mock_game.state.selected_letters = []
        mock_game.state.current_word = ""

        mock_game._handle_letter_click("a")

        assert mock_game.state.selected_letters == []
        assert mock_game.state.current_word == ""

    def test_submit_word_valid(self, mock_game: "KeyboardCoopGame") -> None:
        """Test submitting a valid word adds score."""
        mock_game._generate_random_keyboard = MagicMock()
        mock_game.state.current_word = "cat"
        mock_game.state.selected_letters = ["c", "a", "t"]
        mock_game.state.score = 0

        mock_game._submit_word()

        assert mock_game.state.score == 2  # 2^(3-2) = 2
        assert mock_game.state.current_word == ""
        assert mock_game.state.selected_letters == []

    def test_submit_word_too_short(self, mock_game: "KeyboardCoopGame") -> None:
        """Test submitting too short word gives no score."""
        mock_game.state.current_word = "ca"
        mock_game.state.selected_letters = ["c", "a"]
        mock_game.state.score = 0

        mock_game._submit_word()

        assert mock_game.state.score == 0
        assert "too short" in mock_game.state.message

    def test_submit_word_invalid(self, mock_game: "KeyboardCoopGame") -> None:
        """Test submitting invalid word gives no score."""
        mock_game.state.current_word = "xyz"
        mock_game.state.selected_letters = ["x", "y", "z"]
        mock_game.state.score = 0

        mock_game._submit_word()

        assert mock_game.state.score == 0
        assert "not a valid word" in mock_game.state.message

    def test_reset_game(self, mock_game: "KeyboardCoopGame") -> None:
        """Test reset_game creates new state."""
        mock_game._generate_random_keyboard = MagicMock()
        mock_game.state.score = 100
        mock_game.state.current_word = "test"

        mock_game._reset_game()

        # After reset, state should be fresh
        assert mock_game.state.score == 0
        assert mock_game.state.current_word == ""
        assert mock_game._generate_random_keyboard.called

    def test_get_key_at_position_found(self, mock_game: "KeyboardCoopGame") -> None:
        """Test getting key at position when key exists."""
        mock_rect = MagicMock()
        mock_rect.collidepoint.return_value = True
        mock_game.keyboard.positions = {"a": mock_rect}

        result = mock_game._get_key_at_position((100, 100))
        assert result == "a"

    def test_get_key_at_position_not_found(self, mock_game: "KeyboardCoopGame") -> None:
        """Test getting key at position when no key."""
        mock_rect = MagicMock()
        mock_rect.collidepoint.return_value = False
        mock_game.keyboard.positions = {"a": mock_rect}

        result = mock_game._get_key_at_position((100, 100))
        assert result is None


class TestLoadDictionary:
    """Tests for dictionary loading."""

    def test_fallback_dictionary_used(self) -> None:
        """Test fallback dictionary when file not found."""
        mock_pg = MagicMock()
        mock_pg.font.Font.return_value = MagicMock()
        mock_pg.display.set_mode.return_value = MagicMock()

        with (
            patch.dict("sys.modules", {"pygame": mock_pg}),
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
        ):
            from python_pkg.keyboard_coop.main import KeyboardCoopGame

            game = object.__new__(KeyboardCoopGame)
            dictionary = game._load_dictionary()

        # Should have fallback words
        assert "cat" in dictionary
        assert "dog" in dictionary


class TestGenerateRandomKeyboard:
    """Tests for keyboard layout generation."""

    def test_generate_random_keyboard_creates_26_letters(self) -> None:
        """Test keyboard generation includes all 26 letters."""
        mock_pg = MagicMock()
        mock_pg.Rect = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.keyboard = KeyboardState()

            game._generate_random_keyboard()

        # Should have 26 letters total across all rows
        all_letters = []
        for row in game.keyboard.layout:
            all_letters.extend(row)
        assert len(all_letters) == 26
        assert len(set(all_letters)) == 26  # All unique

    def test_layout_structure_is_10_9_7(self) -> None:
        """Test keyboard layout has correct row structure."""
        mock_pg = MagicMock()
        mock_pg.Rect = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.keyboard = KeyboardState()

            game._generate_random_keyboard()

        assert len(game.keyboard.layout) == 3
        assert len(game.keyboard.layout[0]) == 10
        assert len(game.keyboard.layout[1]) == 9
        assert len(game.keyboard.layout[2]) == 7


class TestCalculateAdjacencies:
    """Tests for adjacency calculation."""

    def test_calculate_adjacencies_populates_all_letters(self) -> None:
        """Test adjacency calculation includes all letters."""
        mock_pg = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.keyboard = KeyboardState()
            game.keyboard.layout = [
                ["a", "b", "c"],
                ["d", "e", "f"],
                ["g", "h"],
            ]

            game._calculate_adjacencies()

        # Each letter should have adjacency list
        assert len(game.keyboard.adjacency) == 8
        # Corner letter should have fewer adjacents
        assert "b" in game.keyboard.adjacency["a"]
        assert "d" in game.keyboard.adjacency["a"]
        assert "e" in game.keyboard.adjacency["a"]


class TestCalculateKeyPositions:
    """Tests for key position calculation."""

    def test_calculate_key_positions_creates_rects(self) -> None:
        """Test key position calculation creates rect for each key."""
        mock_pg = MagicMock()
        mock_pg.Rect = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {"pygame": mock_pg}):
            from python_pkg.keyboard_coop.main import (
                KeyboardCoopGame,
                KeyboardState,
            )

            game = object.__new__(KeyboardCoopGame)
            game.keyboard = KeyboardState()
            game.keyboard.layout = [["a", "b"], ["c", "d"]]

            positions = game._calculate_key_positions()

        assert len(positions) == 4
        assert "a" in positions
        assert "d" in positions

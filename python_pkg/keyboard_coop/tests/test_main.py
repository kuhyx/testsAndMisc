"""Unit tests for keyboard_coop module."""

from unittest.mock import MagicMock, patch

import pytest


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

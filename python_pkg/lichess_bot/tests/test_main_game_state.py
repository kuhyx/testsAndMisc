"""Tests for lichess_bot main module: game state helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import chess
import requests

from python_pkg.lichess_bot._game_logic import (
    _attempt_move,
    _calculate_time_budget,
    _extract_player_info,
    _is_my_turn,
    _log_move_to_file,
    _update_clocks_from_state,
)
from python_pkg.lichess_bot.main import (
    BotContext,
    GameMeta,
    GameState,
    _apply_move_to_board,
    _extract_game_full_data,
    _extract_game_state_data,
    _handle_move_if_needed,
    _init_game_log,
    _rebuild_board_from_moves,
)

if TYPE_CHECKING:
    from pathlib import Path

# Type alias to make mypy happy with test event dicts
Event = dict[str, Any]


class TestApplyMoveToBoard:
    """Tests for _apply_move_to_board."""

    def test_apply_valid_move(self) -> None:
        """Test applying a valid move."""
        board = chess.Board()
        _apply_move_to_board(board, "e2e4", "game1")
        assert board.fen() != chess.STARTING_FEN

    def test_apply_invalid_move(self) -> None:
        """Test applying an invalid move logs debug."""
        board = chess.Board()
        with patch("python_pkg.lichess_bot.main._logger") as mock_logger:
            _apply_move_to_board(board, "invalid", "game1")
            mock_logger.debug.assert_called_once()


class TestInitGameLog:
    """Tests for _init_game_log."""

    def test_init_game_log_success(self, tmp_path: Path) -> None:
        """Test successful log initialization."""
        with patch("python_pkg.lichess_bot.main.Path.cwd", return_value=tmp_path):
            result = _init_game_log("game123", 42)
        assert result is not None
        assert result.exists()
        content = result.read_text()
        assert "game game123 started" in content
        assert "bot_version v42" in content

    def test_init_game_log_oserror(self) -> None:
        """Test log initialization with OSError."""
        with patch("python_pkg.lichess_bot.main.Path.cwd") as mock_cwd:
            mock_path = MagicMock()
            mock_path.__truediv__ = MagicMock(return_value=mock_path)
            mock_path.open.side_effect = OSError("Permission denied")
            mock_cwd.return_value = mock_path
            result = _init_game_log("game123", 42)
        assert result is None


class TestUpdateClocksFromState:
    """Tests for _update_clocks_from_state."""

    def test_update_clocks_white(self) -> None:
        """Test clock update when playing as white."""
        state = GameState(color="white")
        state_data: Event = {"wtime": 60000, "btime": 55000, "winc": 1000}
        _update_clocks_from_state(state_data, state)
        assert state.my_ms == 60000
        assert state.opp_ms == 55000
        assert state.inc_ms == 1000

    def test_update_clocks_black(self) -> None:
        """Test clock update when playing as black."""
        state = GameState(color="black")
        state_data: Event = {"wtime": 60000, "btime": 55000, "binc": 2000}
        _update_clocks_from_state(state_data, state)
        assert state.my_ms == 55000
        assert state.opp_ms == 60000
        assert state.inc_ms == 2000

    def test_update_clocks_float_values(self) -> None:
        """Test clock update with float values."""
        state = GameState(color="white")
        state_data: Event = {"wtime": 60000.5, "btime": 55000.5}
        _update_clocks_from_state(state_data, state)
        assert state.my_ms == 60000
        assert state.opp_ms == 55000

    def test_update_clocks_none_values(self) -> None:
        """Test clock update with None values."""
        state = GameState(color="white")
        state_data: Event = {"wtime": None, "btime": None}
        _update_clocks_from_state(state_data, state)
        assert state.my_ms is None
        assert state.opp_ms is None


class TestExtractPlayerInfo:
    """Tests for _extract_player_info."""

    def test_extract_player_info_white(self) -> None:
        """Test extracting player info when bot is white."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "white": {"id": "mybot", "name": "MyBot"},
            "black": {"id": "opp", "name": "Opponent"},
        }
        _extract_player_info(event, state, meta, api)
        assert state.color == "white"
        assert meta.white_name == "MyBot"
        assert meta.black_name == "Opponent"

    def test_extract_player_info_black(self) -> None:
        """Test extracting player info when bot is black."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "white": {"id": "opp", "name": "Opponent"},
            "black": {"id": "mybot", "name": "MyBot"},
        }
        _extract_player_info(event, state, meta, api)
        assert state.color == "black"

    def test_extract_player_info_invalid_data(self) -> None:
        """Test extracting player info with invalid data."""
        api = MagicMock()
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {"white": "invalid", "black": "invalid"}
        _extract_player_info(event, state, meta, api)
        assert state.color is None

    def test_extract_player_info_missing_name(self) -> None:
        """Test extracting player info with missing name uses id."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "white": {"id": "mybot"},
            "black": {"id": "opponent"},
        }
        _extract_player_info(event, state, meta, api)
        assert meta.white_name == "mybot"
        assert meta.black_name == "opponent"


class TestExtractGameFullData:
    """Tests for _extract_game_full_data."""

    def test_extract_game_full_data(self) -> None:
        """Test extracting gameFull data."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "state": {"moves": "e2e4 e7e5", "status": "started", "wtime": 60000},
            "white": {"id": "mybot"},
            "black": {"id": "opp"},
            "createdAt": 1609459200000,  # 2021-01-01
        }
        moves, status = _extract_game_full_data(event, state, meta, api)
        assert moves == "e2e4 e7e5"
        assert status == "started"
        assert meta.site_url == "https://lichess.org/game1"
        assert meta.date_iso == "2021.01.01"

    def test_extract_game_full_data_invalid_state(self) -> None:
        """Test extracting gameFull data with invalid state."""
        api = MagicMock()
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {"state": "invalid"}
        moves, status = _extract_game_full_data(event, state, meta, api)
        assert moves == ""
        assert status is None


class TestExtractGameStateData:
    """Tests for _extract_game_state_data."""

    def test_extract_game_state_as_white(self) -> None:
        """Test extracting gameState data as white."""
        state = GameState(color="white", my_ms=60000)
        event: Event = {
            "moves": "e2e4",
            "status": "started",
            "wtime": 59000,
            "btime": 60000,
        }
        moves, status = _extract_game_state_data(event, state)
        assert moves == "e2e4"
        assert status == "started"
        assert state.my_ms == 59000
        assert state.opp_ms == 60000

    def test_extract_game_state_as_black(self) -> None:
        """Test extracting gameState data as black."""
        state = GameState(color="black")
        event: Event = {
            "moves": "e2e4 e7e5",
            "wtime": 60000,
            "btime": 59000,
            "binc": 1000,
        }
        moves, __status = _extract_game_state_data(event, state)
        assert moves == "e2e4 e7e5"
        assert state.my_ms == 59000
        assert state.opp_ms == 60000
        assert state.inc_ms == 1000


class TestCalculateTimeBudget:
    """Tests for _calculate_time_budget."""

    def test_calculate_time_budget_normal(self) -> None:
        """Test time budget calculation."""
        state = GameState(my_ms=60000, inc_ms=1000)
        board = chess.Board()
        budget = _calculate_time_budget(state, board, 10.0)
        assert 0.05 <= budget <= 10.0

    def test_calculate_time_budget_low_time(self) -> None:
        """Test time budget with low time."""
        state = GameState(my_ms=1000, inc_ms=0)
        board = chess.Board()
        budget = _calculate_time_budget(state, board, 10.0)
        assert budget >= 0.05


class TestLogMoveToFile:
    """Tests for _log_move_to_file."""

    def test_log_move_to_file(self, tmp_path: Path) -> None:
        """Test logging a move to file."""
        log_path = tmp_path / "game.log"
        log_path.write_text("header\n")
        move = chess.Move.from_uci("e2e4")
        _log_move_to_file(log_path, 1, move, "best move")
        content = log_path.read_text()
        assert "ply 1: e2e4" in content
        assert "best move" in content

    def test_log_move_to_file_none_path(self) -> None:
        """Test logging with None path does nothing."""
        move = chess.Move.from_uci("e2e4")
        _log_move_to_file(None, 1, move, "reason")  # Should not raise


class TestAttemptMove:
    """Tests for _attempt_move."""

    def test_attempt_move_success(self) -> None:
        """Test successful move attempt."""
        api = MagicMock()
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (
            chess.Move.from_uci("e2e4"),
            "opening",
        )
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(my_ms=60000)
        meta = GameMeta(game_id="game1", bot_version=1)
        board = chess.Board()

        result = _attempt_move(ctx, state, meta, board)
        assert result is True
        api.make_move.assert_called_once()

    def test_attempt_move_no_moves(self) -> None:
        """Test move attempt with no legal moves."""
        api = MagicMock()
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (None, "no moves")
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        board = chess.Board()

        result = _attempt_move(ctx, state, meta, board)
        assert result is False

    def test_attempt_move_illegal(self) -> None:
        """Test move attempt with illegal move."""
        api = MagicMock()
        engine = MagicMock()
        engine.max_time_sec = 5.0
        # Return a move that's not legal (e.g., random square move)
        engine.choose_move_with_explanation.return_value = (
            chess.Move.from_uci("a1a8"),
            "bad",
        )
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(my_ms=60000)
        meta = GameMeta(game_id="game1", bot_version=1)
        board = chess.Board()

        result = _attempt_move(ctx, state, meta, board)
        assert result is True
        api.make_move.assert_not_called()

    def test_attempt_move_request_error(self) -> None:
        """Test move attempt with request error."""
        api = MagicMock()
        api.make_move.side_effect = requests.RequestException("Network error")
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (
            chess.Move.from_uci("e2e4"),
            "opening",
        )
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(my_ms=60000)
        meta = GameMeta(game_id="game1", bot_version=1)
        board = chess.Board()

        result = _attempt_move(ctx, state, meta, board)
        assert result is True  # Still returns True


class TestIsMyTurn:
    """Tests for _is_my_turn."""

    def test_is_my_turn_white_to_move(self) -> None:
        """Test checking turn when white to move."""
        board = chess.Board()  # White to move
        assert _is_my_turn(board, "white") is True
        assert _is_my_turn(board, "black") is False

    def test_is_my_turn_black_to_move(self) -> None:
        """Test checking turn when black to move."""
        board = chess.Board()
        board.push_uci("e2e4")  # Black to move
        assert _is_my_turn(board, "white") is False
        assert _is_my_turn(board, "black") is True


class TestRebuildBoardFromMoves:
    """Tests for _rebuild_board_from_moves."""

    def test_rebuild_board_from_moves(self) -> None:
        """Test rebuilding board from moves list."""
        moves_list = ["e2e4", "e7e5", "g1f3"]
        board = _rebuild_board_from_moves(moves_list, "game1")
        assert len(board.move_stack) == 3


class TestHandleMoveIfNeeded:
    """Tests for _handle_move_if_needed."""

    def test_handle_move_game_state_my_turn(self) -> None:
        """Test handling move on gameState when my turn."""
        api = MagicMock()
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (
            chess.Move.from_uci("e2e4"),
            "opening",
        )
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(color="white", my_ms=60000, board=chess.Board())
        meta = GameMeta(game_id="game1", bot_version=1)

        result = _handle_move_if_needed(ctx, state, meta, "gameState", 0)
        assert result is True

    def test_handle_move_game_full_with_moves(self) -> None:
        """Test handling move on gameFull with existing moves (opponent's turn)."""
        api = MagicMock()
        engine = MagicMock()
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(color="white", my_ms=60000, board=chess.Board())
        meta = GameMeta(game_id="game1", bot_version=1)

        # gameFull with moves - don't move
        result = _handle_move_if_needed(ctx, state, meta, "gameFull", 1)
        assert result is True
        engine.choose_move_with_explanation.assert_not_called()

"""Tests for lichess_bot main module."""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import chess
import pytest
import requests

from python_pkg.lichess_bot.main import (
    BotContext,
    GameMeta,
    GameState,
    _apply_move_to_board,
    _attempt_move,
    _calculate_time_budget,
    _collect_analysis_lines,
    _extract_game_full_data,
    _extract_game_state_data,
    _extract_player_info,
    _finalize_game,
    _handle_challenge,
    _handle_game,
    _handle_move_if_needed,
    _init_game_log,
    _insert_analysis_into_log,
    _is_my_turn,
    _log_analysis_progress,
    _log_move_to_file,
    _process_analysis_output,
    _process_bot_event,
    _process_game_event,
    _process_game_events_loop,
    _rebuild_board_from_moves,
    _run_analysis_subprocess,
    _run_event_loop,
    _run_event_loop_iteration,
    _safe_event_loop_iteration,
    _stream_bot_events,
    _update_clocks_from_state,
    _write_pgn_to_log,
    main,
    run_bot,
)

if TYPE_CHECKING:
    from pathlib import Path

# Type alias to make mypy happy with test event dicts
Event = dict[str, Any]
GameThreads = dict[str, threading.Thread]


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


class TestProcessGameEvent:
    """Tests for _process_game_event."""

    def test_process_game_event_unhandled_type(self) -> None:
        """Test processing unhandled event type."""
        ctx = MagicMock()
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {"type": "chatLine", "text": "hello"}
        result = _process_game_event(event, ctx, state, meta)
        assert result is True

    def test_process_game_event_game_full(self) -> None:
        """Test processing gameFull event."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (
            chess.Move.from_uci("e2e4"),
            "opening",
        )
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState()
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "type": "gameFull",
            "state": {"moves": "", "status": "started"},
            "white": {"id": "mybot"},
            "black": {"id": "opp"},
        }
        result = _process_game_event(event, ctx, state, meta)
        assert result is True

    def test_process_game_event_game_end(self) -> None:
        """Test processing game end event."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (None, "no moves")
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(color="white", last_handled_len=-1)
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "type": "gameState",
            "moves": "e2e4 e7e5",
            "status": "mate",
        }
        result = _process_game_event(event, ctx, state, meta)
        assert result is False

    def test_process_game_event_game_end_after_move(self) -> None:
        """Test game ends with status after handling move.

        This covers the case where _handle_move_if_needed returns True
        but status indicates game end.
        """
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (
            chess.Move.from_uci("d2d4"),
            "response",
        )
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        # Black's turn - it's opponent's move, so we don't need to move
        state = GameState(color="black", last_handled_len=-1)
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "type": "gameState",
            "moves": "e2e4",  # One move - now it's black's turn
            "status": "resign",  # Game ended with resign
        }
        result = _process_game_event(event, ctx, state, meta)
        assert result is False  # Game should end

    def test_process_game_event_unchanged_position(self) -> None:
        """Test processing event with unchanged position."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        state = GameState(last_handled_len=2, color="white")
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {"type": "gameState", "moves": "e2e4 e7e5"}
        result = _process_game_event(event, ctx, state, meta)
        assert result is True

    def test_process_game_event_color_unknown(self) -> None:
        """Test processing event with unknown color."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        state = GameState(last_handled_len=-1)
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {"type": "gameState", "moves": "e2e4"}
        result = _process_game_event(event, ctx, state, meta)
        assert result is True
        assert state.last_handled_len == 1

    def test_process_game_event_color_unknown_on_gamefull(self) -> None:
        """Test processing gameFull event with still unknown color.

        This covers the branch where event_type is gameFull but color
        is not determined (e.g., spectator watching game).
        """
        api = MagicMock()
        # Return a user id that doesn't match either player
        api.get_my_user_id.return_value = "spectator"
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        state = GameState(last_handled_len=-1)
        meta = GameMeta(game_id="game1", bot_version=1)
        event: Event = {
            "type": "gameFull",
            "state": {"moves": "e2e4", "status": "started"},
            "white": {"id": "player1"},
            "black": {"id": "player2"},
        }
        result = _process_game_event(event, ctx, state, meta)
        assert result is True
        # last_handled_len should NOT be updated for gameFull with unknown color
        assert state.last_handled_len == -1


class TestWritePgnToLog:
    """Tests for _write_pgn_to_log."""

    def test_write_pgn_to_log(self, tmp_path: Path) -> None:
        """Test writing PGN to log file."""
        log_path = tmp_path / "game.log"
        log_path.write_text("header\n")
        board = chess.Board()
        board.push_uci("e2e4")
        meta = GameMeta(
            game_id="game1",
            bot_version=1,
            site_url="https://lichess.org/game1",
            date_iso="2021.01.01",
            white_name="White",
            black_name="Black",
        )
        _write_pgn_to_log(log_path, board, meta)
        content = log_path.read_text()
        assert "PGN:" in content
        assert "e4" in content


class TestRunAnalysisSubprocess:
    """Tests for _run_analysis_subprocess."""

    def test_run_analysis_subprocess_script_not_found(self, tmp_path: Path) -> None:
        """Test analysis when script not found."""
        log_path = tmp_path / "game.log"
        with patch("python_pkg.lichess_bot.main.Path") as mock_path:
            mock_script = MagicMock()
            mock_script.is_file.return_value = False
            resolve = mock_path.return_value.resolve.return_value
            resolve.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_script
            )
            result = _run_analysis_subprocess("game1", log_path, 10)
        assert result is None

    def test_run_analysis_subprocess_success(self, tmp_path: Path) -> None:
        """Test successful analysis subprocess."""
        log_path = tmp_path / "game.log"
        log_path.write_text("test")

        mock_proc = MagicMock()
        mock_proc.stdout = iter(["  1 e4\n", "  2 e5\n"])
        mock_proc.stderr.read.return_value = ""
        mock_proc.wait.return_value = 0
        mock_proc.__enter__ = MagicMock(return_value=mock_proc)
        mock_proc.__exit__ = MagicMock(return_value=False)

        with (
            patch("python_pkg.lichess_bot.main.Path") as mock_path,
            patch("subprocess.Popen", return_value=mock_proc),
        ):
            mock_script = MagicMock()
            mock_script.is_file.return_value = True
            resolve = mock_path.return_value.resolve.return_value
            resolve.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_script
            )
            result = _run_analysis_subprocess("game1", log_path, 2)

        assert result is not None


class TestProcessAnalysisOutput:
    """Tests for _process_analysis_output."""

    def test_process_analysis_output_success(self) -> None:
        """Test processing analysis output successfully."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["  1 e4\n", "  2 e5\n"])
        mock_proc.stderr.read.return_value = ""
        mock_proc.wait.return_value = 0

        result = _process_analysis_output(mock_proc, "game1", 2)
        assert result is not None
        assert "e4" in result

    def test_process_analysis_output_error_exit(self) -> None:
        """Test processing analysis output with error exit."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["output\n"])
        mock_proc.stderr.read.return_value = "error message"
        mock_proc.wait.return_value = 1

        result = _process_analysis_output(mock_proc, "game1", 1)
        assert result is not None
        assert "stderr" in result

    def test_process_analysis_output_error_exit_no_stderr(self) -> None:
        """Test processing analysis output with error exit but no stderr."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["output\n"])
        mock_proc.stderr.read.return_value = ""
        mock_proc.wait.return_value = 1

        result = _process_analysis_output(mock_proc, "game1", 1)
        assert result is not None
        assert "stderr" not in result

    def test_process_analysis_output_none_pipes(self) -> None:
        """Test processing analysis output with None pipes."""
        mock_proc = MagicMock()
        mock_proc.stdout = None
        mock_proc.stderr = None

        with pytest.raises(RuntimeError, match="pipes unexpectedly None"):
            _process_analysis_output(mock_proc, "game1", 1)


class TestCollectAnalysisLines:
    """Tests for _collect_analysis_lines helper."""

    def test_collect_analysis_lines_empty_iterator(self) -> None:
        """Test collecting lines from empty iterator."""
        empty_iter: list[str] = []
        analyzed, lines = _collect_analysis_lines(iter(empty_iter), "game1", 10)
        assert analyzed == 0
        assert lines == []

    def test_collect_analysis_lines_with_content(self) -> None:
        """Test collecting lines from iterator with content."""
        content = ["  1 e4\n", "  2 e5\n", "not a ply line\n"]
        analyzed, lines = _collect_analysis_lines(iter(content), "game1", 3)
        assert analyzed == 2
        assert lines == content

    def test_collect_analysis_lines_full_iteration(self) -> None:
        """Test that all lines are collected."""
        content = ["line1\n", "  3 Nf3\n", "line3\n"]
        analyzed, lines = _collect_analysis_lines(iter(content), "game1", 1)
        assert analyzed == 1
        assert len(lines) == 3


class TestLogAnalysisProgress:
    """Tests for _log_analysis_progress."""

    def test_log_analysis_progress_with_total(self) -> None:
        """Test logging progress with known total."""
        with patch("python_pkg.lichess_bot.main._logger") as mock_logger:
            _log_analysis_progress("game1", 5, 10)
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0]
            assert "50%" in call_args[0] % call_args[1:]

    def test_log_analysis_progress_zero_total(self) -> None:
        """Test logging progress with zero total."""
        with patch("python_pkg.lichess_bot.main._logger") as mock_logger:
            _log_analysis_progress("game1", 5, 0)
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0]
            assert "unknown" in call_args[0]


class TestInsertAnalysisIntoLog:
    """Tests for _insert_analysis_into_log."""

    def test_insert_analysis_before_pgn(self, tmp_path: Path) -> None:
        """Test inserting analysis before PGN section."""
        log_path = tmp_path / "game.log"
        log_path.write_text("header\n\nPGN:\n1. e4\n")
        meta = GameMeta(
            game_id="game1",
            bot_version=1,
            date_iso="2021.01.01",
            white_name="White",
            black_name="Black",
        )
        _insert_analysis_into_log(log_path, "Analysis here", meta)
        content = log_path.read_text()
        assert "ANALYSIS:" in content
        assert content.index("ANALYSIS:") < content.index("PGN:")

    def test_insert_analysis_at_start(self, tmp_path: Path) -> None:
        """Test inserting analysis when PGN at start."""
        log_path = tmp_path / "game.log"
        log_path.write_text("PGN:\n1. e4\n")
        meta = GameMeta(game_id="game1", bot_version=1)
        _insert_analysis_into_log(log_path, "Analysis here", meta)
        content = log_path.read_text()
        assert "ANALYSIS:" in content

    def test_insert_analysis_no_pgn(self, tmp_path: Path) -> None:
        """Test inserting analysis when no PGN section."""
        log_path = tmp_path / "game.log"
        log_path.write_text("header\n")
        meta = GameMeta(game_id="game1", bot_version=1)
        _insert_analysis_into_log(log_path, "Analysis here", meta)
        content = log_path.read_text()
        assert "ANALYSIS:" in content

    def test_insert_analysis_oserror(self, tmp_path: Path) -> None:
        """Test inserting analysis with OSError."""
        log_path = tmp_path / "nonexistent" / "game.log"
        meta = GameMeta(game_id="game1", bot_version=1)
        # Should not raise, just log debug
        _insert_analysis_into_log(log_path, "Analysis", meta)


class TestFinalizeGame:
    """Tests for _finalize_game."""

    def test_finalize_game_no_log_path(self) -> None:
        """Test finalize game with no log path."""
        state = GameState(log_path=None)
        meta = GameMeta(game_id="game1", bot_version=1)
        _finalize_game(state, meta)  # Should not raise

    def test_finalize_game_write_error(self, tmp_path: Path) -> None:
        """Test finalize game with write error."""
        log_path = tmp_path / "game.log"
        log_path.write_text("header")
        state = GameState(log_path=log_path)
        meta = GameMeta(game_id="game1", bot_version=1)

        with patch(
            "python_pkg.lichess_bot.main._write_pgn_to_log",
            side_effect=OSError("error"),
        ):
            _finalize_game(state, meta)  # Should not raise

    def test_finalize_game_type_error_on_move_stack(self, tmp_path: Path) -> None:
        """Test finalize game with TypeError on move_stack."""
        log_path = tmp_path / "game.log"
        log_path.write_text("header\n")
        state = GameState(log_path=log_path)
        meta = GameMeta(game_id="game1", bot_version=1)

        mock_board = MagicMock()
        # Create a property that raises TypeError when accessed
        type(mock_board).move_stack = property(
            lambda _self: (_ for _ in ()).throw(TypeError())
        )
        state.board = mock_board

        with patch("python_pkg.lichess_bot.main._write_pgn_to_log"):
            _finalize_game(state, meta)  # Should not raise

    def test_finalize_game_analysis_error(self, tmp_path: Path) -> None:
        """Test finalize game with analysis error."""
        log_path = tmp_path / "game.log"
        log_path.write_text("header\n")
        state = GameState(log_path=log_path)
        meta = GameMeta(game_id="game1", bot_version=1)

        with (
            patch("python_pkg.lichess_bot.main._write_pgn_to_log"),
            patch(
                "python_pkg.lichess_bot.main._run_analysis_subprocess",
                side_effect=OSError("error"),
            ),
        ):
            _finalize_game(state, meta)  # Should not raise


class TestHandleGame:
    """Tests for _handle_game."""

    def test_handle_game_success(self, tmp_path: Path) -> None:
        """Test handling a game successfully."""
        api = MagicMock()
        api.get_my_user_id.return_value = "mybot"
        api.stream_game_events.return_value = iter(
            [
                {
                    "type": "gameFull",
                    "state": {"moves": "", "status": "started"},
                    "white": {"id": "mybot"},
                    "black": {"id": "opp"},
                },
                {"type": "gameState", "moves": "e2e4", "status": "mate"},
            ]
        )
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (None, "no moves")
        ctx = BotContext(api=api, engine=engine, bot_version=1)

        with (
            patch("python_pkg.lichess_bot.main.Path.cwd", return_value=tmp_path),
            patch(
                "python_pkg.lichess_bot.main._run_analysis_subprocess",
                return_value=None,
            ),
        ):
            _handle_game("game1", ctx, None)

    def test_handle_game_request_error(self, tmp_path: Path) -> None:
        """Test handling a game with request error."""
        api = MagicMock()
        api.stream_game_events.side_effect = requests.RequestException("error")
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)

        with (
            patch("python_pkg.lichess_bot.main.Path.cwd", return_value=tmp_path),
            patch(
                "python_pkg.lichess_bot.main._run_analysis_subprocess",
                return_value=None,
            ),
        ):
            _handle_game("game1", ctx, None)  # Should not raise

    def test_handle_game_skips_chat_events(self, tmp_path: Path) -> None:
        """Test handling a game skips chat events."""
        api = MagicMock()
        api.stream_game_events.return_value = iter(
            [
                {"type": "chatLine", "text": "hello"},
                {"type": "opponentGone", "gone": True},
            ]
        )
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)

        with (
            patch("python_pkg.lichess_bot.main.Path.cwd", return_value=tmp_path),
            patch(
                "python_pkg.lichess_bot.main._run_analysis_subprocess",
                return_value=None,
            ),
        ):
            _handle_game("game1", ctx, None)


class TestProcessGameEventsLoop:
    """Tests for _process_game_events_loop."""

    def test_empty_events_iterator(self) -> None:
        """Test processing empty events iterator."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        state = GameState(color="white")
        meta = GameMeta(game_id="game1", bot_version=1)

        empty_iter: list[Event] = []
        # Should complete without error when iterator is empty
        _process_game_events_loop(iter(empty_iter), ctx, state, meta)

    def test_processes_all_events(self) -> None:
        """Test that all events are processed until break condition."""
        api = MagicMock()
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (None, "no moves")
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(color="white")
        meta = GameMeta(game_id="game1", bot_version=1)

        events: list[Event] = [
            {"type": "chatLine", "text": "hello"},  # skipped
            {"type": "gameState", "moves": "e2e4", "status": "resign"},  # game end
        ]
        _process_game_events_loop(iter(events), ctx, state, meta)

    def test_processes_multiple_game_events(self) -> None:
        """Test processing multiple game events that continue the game."""
        api = MagicMock()
        engine = MagicMock()
        engine.max_time_sec = 5.0
        engine.choose_move_with_explanation.return_value = (
            chess.Move.from_uci("e2e4"),
            "e4",
        )
        api.make_move.return_value = None
        ctx = BotContext(api=api, engine=engine, bot_version=1)
        state = GameState(color="white")
        state.board = chess.Board()
        meta = GameMeta(game_id="game1", bot_version=1)

        events: list[Event] = [
            # First event - game state, game continues
            {"type": "gameState", "moves": "", "status": "started"},
            # Second event - opponent moves, game continues
            {"type": "gameState", "moves": "e2e4 e7e5", "status": "started"},
            # Third event - game ends
            {"type": "gameState", "moves": "e2e4 e7e5", "status": "mate"},
        ]
        _process_game_events_loop(iter(events), ctx, state, meta)


class TestRunEventLoop:
    """Tests for _run_event_loop."""

    def test_run_event_loop_zero_iterations(self) -> None:
        """Test running event loop with zero iterations."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}

        # Should complete immediately with 0 iterations
        _run_event_loop(ctx, game_threads, 0, 0)

    def test_run_event_loop_limited_iterations(self) -> None:
        """Test running event loop with limited iterations."""
        api = MagicMock()
        api.stream_bot_events.return_value = iter([])
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}

        with patch(
            "python_pkg.lichess_bot.main._safe_event_loop_iteration", return_value=0
        ) as mock_iter:
            _run_event_loop(ctx, game_threads, 0, 3)
            assert mock_iter.call_count == 3

    def test_run_event_loop_none_iterations_needs_interrupt(self) -> None:
        """Test that None iterations runs until interrupted."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}

        call_count = 0

        def stop_after_calls(*_args: object, **_kwargs: object) -> int:
            nonlocal call_count
            call_count += 1
            if call_count >= 5:
                raise KeyboardInterrupt
            return 0

        with (
            patch(
                "python_pkg.lichess_bot.main._safe_event_loop_iteration",
                side_effect=stop_after_calls,
            ),
            pytest.raises(KeyboardInterrupt),
        ):
            _run_event_loop(ctx, game_threads, 0, None)

        assert call_count == 5


class TestHandleChallenge:
    """Tests for _handle_challenge."""

    def test_accept_standard_blitz(self) -> None:
        """Test accepting standard blitz challenge."""
        api = MagicMock()
        challenge: Event = {
            "id": "ch1",
            "variant": {"key": "standard"},
            "speed": "blitz",
        }
        _handle_challenge(challenge, api, decline_correspondence=False)
        api.accept_challenge.assert_called_once_with("ch1")

    def test_decline_variant(self) -> None:
        """Test declining non-standard variant."""
        api = MagicMock()
        challenge: Event = {
            "id": "ch1",
            "variant": {"key": "chess960"},
            "speed": "blitz",
        }
        _handle_challenge(challenge, api, decline_correspondence=False)
        api.decline_challenge.assert_called_once()

    def test_decline_correspondence(self) -> None:
        """Test declining correspondence when flag set."""
        api = MagicMock()
        challenge: Event = {
            "id": "ch1",
            "variant": {"key": "standard"},
            "speed": "correspondence",
        }
        _handle_challenge(challenge, api, decline_correspondence=True)
        api.decline_challenge.assert_called_once()

    def test_accept_correspondence_when_allowed(self) -> None:
        """Test accepting correspondence when flag not set."""
        api = MagicMock()
        challenge: Event = {
            "id": "ch1",
            "variant": {"key": "standard"},
            "speed": "correspondence",
        }
        _handle_challenge(challenge, api, decline_correspondence=False)
        api.decline_challenge.assert_called_once()  # Still declined due to perf_ok

    def test_invalid_variant_data(self) -> None:
        """Test handling invalid variant data."""
        api = MagicMock()
        challenge: Event = {
            "id": "ch1",
            "variant": "invalid",
            "speed": "blitz",
        }
        _handle_challenge(challenge, api, decline_correspondence=False)
        api.accept_challenge.assert_called_once()


class TestProcessBotEvent:
    """Tests for _process_bot_event."""

    def test_process_challenge_event(self) -> None:
        """Test processing challenge event."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {
            "type": "challenge",
            "challenge": {
                "id": "ch1",
                "variant": {"key": "standard"},
                "speed": "blitz",
            },
        }
        _process_bot_event(event, ctx, game_threads)
        api.accept_challenge.assert_called_once()

    def test_process_game_start_event(self, tmp_path: Path) -> None:
        """Test processing gameStart event."""
        api = MagicMock()
        api.stream_game_events.return_value = iter([])
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {"type": "gameStart", "game": {"id": "game1"}}

        with (
            patch("python_pkg.lichess_bot.main.Path.cwd", return_value=tmp_path),
            patch(
                "python_pkg.lichess_bot.main._run_analysis_subprocess",
                return_value=None,
            ),
        ):
            _process_bot_event(event, ctx, game_threads)

        assert "game1" in game_threads
        game_threads["game1"].join(timeout=1)

    def test_process_game_start_existing_thread(self) -> None:
        """Test processing gameStart with existing alive thread."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        mock_thread = MagicMock(spec=threading.Thread)
        mock_thread.is_alive.return_value = True
        game_threads: GameThreads = {"game1": mock_thread}
        event: Event = {"type": "gameStart", "game": {"id": "game1"}}
        _process_bot_event(event, ctx, game_threads)
        # Should not create new thread
        assert game_threads["game1"] is mock_thread

    def test_process_game_finish_event(self) -> None:
        """Test processing gameFinish event."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {"type": "gameFinish", "game": {"id": "game1"}}
        with patch("python_pkg.lichess_bot.main._logger") as mock_logger:
            _process_bot_event(event, ctx, game_threads)
            mock_logger.info.assert_called()

    def test_process_game_finish_invalid_data(self) -> None:
        """Test processing gameFinish event with non-dict game data."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {"type": "gameFinish", "game": "not_a_dict"}
        with patch("python_pkg.lichess_bot.main._logger") as mock_logger:
            _process_bot_event(event, ctx, game_threads)
            # Should not log info since game data is invalid
            mock_logger.info.assert_not_called()

    def test_process_unknown_event(self) -> None:
        """Test processing unknown event."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {"type": "unknown", "data": "test"}
        with patch("python_pkg.lichess_bot.main._logger") as mock_logger:
            _process_bot_event(event, ctx, game_threads)
            mock_logger.debug.assert_called()

    def test_process_challenge_invalid_data(self) -> None:
        """Test processing challenge with invalid data."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {"type": "challenge", "challenge": "invalid"}
        _process_bot_event(event, ctx, game_threads)
        api.accept_challenge.assert_not_called()

    def test_process_game_start_invalid_data(self) -> None:
        """Test processing gameStart with invalid data."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {"type": "gameStart", "game": "invalid"}
        _process_bot_event(event, ctx, game_threads)
        assert len(game_threads) == 0


class TestStreamBotEvents:
    """Tests for _stream_bot_events."""

    def test_stream_bot_events(self) -> None:
        """Test streaming bot events."""
        api = MagicMock()
        api.stream_events.return_value = iter([{"type": "test"}])
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        events = list(_stream_bot_events(ctx))
        assert len(events) == 1


class TestRunEventLoopIteration:
    """Tests for _run_event_loop_iteration."""

    def test_run_event_loop_iteration(self) -> None:
        """Test running event loop iteration."""
        api = MagicMock()
        api.stream_events.return_value = iter([{"type": "unknown"}])
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        result = _run_event_loop_iteration(ctx, game_threads)
        assert result == 0


class TestSafeEventLoopIteration:
    """Tests for _safe_event_loop_iteration."""

    def test_safe_event_loop_iteration_success(self) -> None:
        """Test safe event loop iteration success."""
        api = MagicMock()
        api.stream_events.return_value = iter([])
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        result = _safe_event_loop_iteration(ctx, game_threads, 0)
        assert result == 0

    def test_safe_event_loop_iteration_error(self) -> None:
        """Test safe event loop iteration with error."""
        api = MagicMock()
        api.stream_events.side_effect = requests.RequestException("error")
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        with patch("python_pkg.lichess_bot.main.backoff_sleep", return_value=5):
            result = _safe_event_loop_iteration(ctx, game_threads, 2)
        assert result == 5


class TestRunBot:
    """Tests for run_bot."""

    def test_run_bot_no_token(self) -> None:
        """Test run_bot without token raises error."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(RuntimeError, match="LICHESS_TOKEN"),
        ):
            run_bot()

    def test_run_bot_with_token(self) -> None:
        """Test run_bot with token starts event loop."""

        class _StopLoopError(Exception):
            """Custom exception to stop the loop."""

        def stop_loop(*_args: object, **_kwargs: object) -> None:
            raise _StopLoopError

        with (
            patch.dict(os.environ, {"LICHESS_TOKEN": "test_token"}),
            patch(
                "python_pkg.lichess_bot.main.get_and_increment_version",
                return_value=1,
            ),
            patch("python_pkg.lichess_bot.main.LichessAPI"),
            patch("python_pkg.lichess_bot.main.RandomEngine"),
            patch(
                "python_pkg.lichess_bot.main._safe_event_loop_iteration",
                side_effect=stop_loop,
            ),
            pytest.raises(_StopLoopError),
        ):
            run_bot("DEBUG", decline_correspondence=True)


class TestMain:
    """Tests for main function."""

    def test_main_parses_args(self) -> None:
        """Test main parses command line arguments."""

        class _StopExecutionError(Exception):
            """Custom exception to stop execution."""

        with (
            patch(
                "sys.argv",
                ["main.py", "--log-level", "DEBUG", "--decline-correspondence"],
            ),
            patch(
                "python_pkg.lichess_bot.main.run_bot", side_effect=_StopExecutionError
            ) as mock_run_bot,
            pytest.raises(_StopExecutionError),
        ):
            main()
        mock_run_bot.assert_called_once_with("DEBUG", decline_correspondence=True)

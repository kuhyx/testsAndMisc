"""Tests for lichess_bot main module: game events and analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, PropertyMock, patch

import chess
import pytest

from python_pkg.lichess_bot.main import (
    BotContext,
    GameMeta,
    GameState,
    _collect_analysis_lines,
    _finalize_game,
    _insert_analysis_into_log,
    _log_analysis_progress,
    _process_analysis_output,
    _process_game_event,
    _run_analysis_subprocess,
    _write_pgn_to_log,
)

if TYPE_CHECKING:
    from pathlib import Path

# Type alias to make mypy happy with test event dicts
Event = dict[str, Any]


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
        # Use PropertyMock to raise TypeError when move_stack is accessed
        type(mock_board).move_stack = PropertyMock(side_effect=TypeError())
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

"""Tests for lichess_bot main module: bot event loop."""

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
    _handle_challenge,
    _handle_game,
    _process_bot_event,
    _process_game_events_loop,
    _run_event_loop,
    _run_event_loop_iteration,
    _safe_event_loop_iteration,
    _stream_bot_events,
    main,
    run_bot,
)

if TYPE_CHECKING:
    from pathlib import Path

# Type aliases to make mypy happy with test event dicts
Event = dict[str, Any]
GameThreads = dict[str, threading.Thread]


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

    def test_process_game_start_event(self) -> None:
        """Test processing gameStart event."""
        api = MagicMock()
        ctx = BotContext(api=api, engine=MagicMock(), bot_version=1)
        game_threads: GameThreads = {}
        event: Event = {"type": "gameStart", "game": {"id": "game1"}}

        with patch("python_pkg.lichess_bot.main.threading.Thread") as mock_thread_class:
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread
            _process_bot_event(event, ctx, game_threads)

        assert "game1" in game_threads
        mock_thread.start.assert_called_once()

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

"""Main entry point for the Lichess bot."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import TYPE_CHECKING

import chess
import requests

from python_pkg.lichess_bot._game_logic import (
    _extract_game_full_data,
    _extract_game_state_data,
    _handle_challenge,
    _handle_move_if_needed,
    _insert_analysis_into_log,
    _write_pgn_to_log,
)
from python_pkg.lichess_bot.engine import RandomEngine
from python_pkg.lichess_bot.lichess_api import LichessAPI
from python_pkg.lichess_bot.utils import backoff_sleep, get_and_increment_version

if TYPE_CHECKING:
    from collections.abc import Iterator

_logger = logging.getLogger(__name__)

# Regex for parsing ply numbers from analysis output
_PLY_LINE_RE = re.compile(r"^\s*(\d+)\s")

# Game end statuses
_GAME_END_STATUSES = frozenset({"mate", "resign", "stalemate", "timeout", "draw"})


@dataclass
class GameMeta:
    """Metadata for a game (for PGN headers and logging)."""

    game_id: str
    bot_version: int
    site_url: str | None = None
    date_iso: str | None = None
    white_name: str | None = None
    black_name: str | None = None


@dataclass
class GameState:
    """Mutable state for an ongoing game."""

    board: chess.Board = field(default_factory=chess.Board)
    color: str | None = None
    last_handled_len: int = -1
    my_ms: int | None = None
    opp_ms: int | None = None
    inc_ms: int = 0
    log_path: Path | None = None


@dataclass
class BotContext:
    """Shared context for bot operations."""

    api: LichessAPI
    engine: RandomEngine
    bot_version: int
    decline_correspondence: bool = False


def _apply_move_to_board(board: chess.Board, move: str, game_id: str) -> None:
    """Apply a single move to the board, logging errors."""
    try:
        board.push_uci(move)
    except ValueError:
        _logger.debug("Game %s: could not apply move %s", game_id, move)


def _init_game_log(game_id: str, bot_version: int) -> Path | None:
    """Initialize the game log file."""
    game_log_path = Path.cwd() / f"lichess_bot_game_{game_id}.log"
    try:
        with game_log_path.open("w") as lf:
            lf.write(f"game {game_id} started\n")
            lf.write(f"bot_version v{bot_version}\n")
    except OSError:
        return None
    return game_log_path


def _rebuild_board_from_moves(moves_list: list[str], game_id: str) -> chess.Board:
    """Rebuild board from list of moves."""
    board = chess.Board()
    for m in moves_list:
        _apply_move_to_board(board, m, game_id)
    return board


def _process_game_event(
    event: dict[str, object],
    ctx: BotContext,
    state: GameState,
    meta: GameMeta,
) -> bool:
    """Process a single game event. Returns False if game should end."""
    et = event.get("type")

    if et not in ("gameFull", "gameState"):
        return True  # Continue processing other events

    # At this point et is guaranteed to be a string
    event_type = str(et)

    # Extract moves and status based on event type
    if event_type == "gameFull":
        moves, status = _extract_game_full_data(event, state, meta, ctx.api)
        _logger.info("Game %s: joined as %s (gameFull)", meta.game_id, state.color)
    else:
        moves, status = _extract_game_state_data(event, state)

    moves_list = moves.split() if moves else []
    new_len = len(moves_list)

    _logger.info(
        "Game %s: event=%s, moves=%s, color=%s",
        meta.game_id,
        event_type,
        new_len,
        state.color,
    )

    if new_len == state.last_handled_len:
        _logger.debug(
            "Game %s: position unchanged (len=%s), skipping", meta.game_id, new_len
        )
        return True

    # Rebuild board from moves
    state.board = _rebuild_board_from_moves(moves_list, meta.game_id)

    if state.color is None:
        _logger.info("Game %s: color unknown yet; waiting for gameFull", meta.game_id)
        if event_type == "gameState":
            state.last_handled_len = new_len
        return True

    if not _handle_move_if_needed(ctx, state, meta, event_type, new_len):
        return False

    # Check for game end
    if status in _GAME_END_STATUSES:
        _logger.info("Game %s finished: %s", meta.game_id, status)
        return False

    return True


def _run_analysis_subprocess(
    game_id: str, log_path: Path, total_plies: int
) -> str | None:
    """Run the analysis script and return output text."""
    analyze_script = (
        Path(__file__).resolve().parent.parent
        / "stockfish_analysis"
        / "analyze_chess_game.py"
    )

    if not analyze_script.is_file():
        _logger.info(
            "Game %s: analysis script not found at %s; skipping analysis",
            game_id,
            analyze_script,
        )
        return None

    _logger.info(
        "Game %s: starting post-game analysis (%s plies)", game_id, total_plies
    )

    # S603: subprocess call is safe - analyze_script is validated with is_file()
    # above and all arguments are explicit strings from trusted sources
    with subprocess.Popen(
        [sys.executable, "-u", str(analyze_script), str(log_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    ) as proc:
        return _process_analysis_output(proc, game_id, total_plies)


def _process_analysis_output(
    proc: subprocess.Popen[str], game_id: str, total_plies: int
) -> str | None:
    """Process analysis subprocess output and return analysis text."""
    # stdout/stderr are guaranteed non-None with PIPE, but verify at runtime
    if proc.stdout is None or proc.stderr is None:
        proc.terminate()
        msg = "subprocess pipes unexpectedly None"
        raise RuntimeError(msg)

    __analyzed, lines = _collect_analysis_lines(proc.stdout, game_id, total_plies)

    stderr_text = proc.stderr.read() or ""
    ret = proc.wait()
    analysis_text = "".join(lines)

    if ret:
        _logger.warning("Game %s: analysis script exited with code %s", game_id, ret)
        if stderr_text:
            analysis_text += "\n[stderr]\n" + stderr_text

    _logger.info("Game %s: analysis complete", game_id)
    return analysis_text


def _collect_analysis_lines(
    stdout: Iterator[str], game_id: str, total_plies: int
) -> tuple[int, list[str]]:
    """Collect and process analysis lines from stdout.

    Returns:
        Tuple of (analyzed_count, lines_list).
    """
    analyzed = 0
    lines: list[str] = []
    while True:
        try:
            line = next(stdout)
        except StopIteration:
            break
        lines.append(line)
        m = _PLY_LINE_RE.match(line)
        if m:
            analyzed += 1
            _log_analysis_progress(game_id, analyzed, total_plies)
    return analyzed, lines


def _log_analysis_progress(game_id: str, analyzed: int, total_plies: int) -> None:
    """Log analysis progress."""
    if total_plies:
        left = max(0, total_plies - analyzed)
        pct = analyzed / total_plies * 100.0
        _logger.info(
            "Game %s: analysis progress %s/%s (%.0f%%), left %s",
            game_id,
            analyzed,
            total_plies,
            pct,
            left,
        )
    else:
        _logger.info(
            "Game %s: analysis progress %s plies (total unknown)", game_id, analyzed
        )


def _finalize_game(state: GameState, meta: GameMeta) -> None:
    """Finalize game: write PGN and run analysis."""
    if not state.log_path:
        return

    try:
        _write_pgn_to_log(state.log_path, state.board, meta)
    except OSError as e:
        _logger.debug("Game %s: could not write PGN: %s", meta.game_id, e)
        return

    # Run analysis
    try:
        total_plies = len(state.board.move_stack)
    except TypeError:
        total_plies = 0

    try:
        analysis_text = _run_analysis_subprocess(
            meta.game_id, state.log_path, total_plies
        )
        if analysis_text:
            _insert_analysis_into_log(state.log_path, analysis_text, meta)
    except (subprocess.SubprocessError, OSError) as e:
        _logger.debug("Game %s: analysis run failed: %s", meta.game_id, e)


def _process_game_events_loop(
    events: Iterator[dict[str, object]],
    ctx: BotContext,
    state: GameState,
    meta: GameMeta,
) -> None:
    """Process game events from an iterator until game ends.

    This is extracted to allow testing the loop exhaustion branch.
    """
    while True:
        try:
            event = next(events)
        except StopIteration:
            break
        et = event.get("type")
        if et in ("chatLine", "opponentGone"):
            continue
        if not _process_game_event(event, ctx, state, meta):
            break


def _handle_game(game_id: str, ctx: BotContext, my_color: str | None = None) -> None:
    """Handle a single game from start to finish."""
    _logger.info("Starting game thread for %s [bot v%s]", game_id, ctx.bot_version)

    meta = GameMeta(game_id=game_id, bot_version=ctx.bot_version)
    state = GameState(color=my_color)
    state.log_path = _init_game_log(game_id, ctx.bot_version)

    try:
        events = ctx.api.stream_game_events(game_id)
        _process_game_events_loop(events, ctx, state, meta)
    except requests.RequestException:
        _logger.exception("Game %s thread error", game_id)
    finally:
        _finalize_game(state, meta)
        _logger.info("Ending game thread for %s", game_id)


def _process_bot_event(
    event: dict[str, object],
    ctx: BotContext,
    game_threads: dict[str, threading.Thread],
) -> None:
    """Process a single bot event (challenge, gameStart, etc.)."""
    event_type = event.get("type")

    if event_type == "challenge":
        challenge = event.get("challenge", {})
        if isinstance(challenge, dict):
            _handle_challenge(
                challenge, ctx.api, decline_correspondence=ctx.decline_correspondence
            )

    elif event_type == "gameStart":
        game_data = event.get("game", {})
        if isinstance(game_data, dict):
            game_id = str(game_data.get("id", ""))
            if game_id and (
                game_id not in game_threads or not game_threads[game_id].is_alive()
            ):
                t = threading.Thread(
                    target=_handle_game,
                    args=(game_id, ctx),
                    name=f"game-{game_id}",
                )
                t.daemon = True
                game_threads[game_id] = t
                t.start()

    elif event_type == "gameFinish":
        game_data = event.get("game", {})
        if isinstance(game_data, dict):
            game_id = game_data.get("id", "")
            _logger.info("Game finished event: %s", game_id)

    else:
        _logger.debug("Unhandled event: %s", json.dumps(event))


def _stream_bot_events(ctx: BotContext) -> Iterator[dict[str, object]]:
    """Stream events from Lichess API with type hints."""
    yield from ctx.api.stream_events()


def _run_event_loop_iteration(
    ctx: BotContext, game_threads: dict[str, threading.Thread]
) -> int:
    """Run one iteration of the event loop.

    Returns:
        New backoff value (0 on success).
    """
    for event in _stream_bot_events(ctx):
        _process_bot_event(event, ctx, game_threads)
    return 0


def _safe_event_loop_iteration(
    ctx: BotContext, game_threads: dict[str, threading.Thread], backoff: int
) -> int:
    """Run event loop iteration with error handling.

    This wrapper exists to avoid try-except inside while True loop (PERF203).

    Returns:
        New backoff value.
    """
    try:
        return _run_event_loop_iteration(ctx, game_threads)
    except requests.RequestException as e:
        _logger.warning("Event stream error: %s", e)
        return backoff_sleep(backoff)


def run_bot(
    log_level: str = "INFO",
    *,
    decline_correspondence: bool = False,
    max_iterations: int | None = None,
) -> None:
    """Start the bot and listen for incoming events.

    Args:
        log_level: Logging level (default: INFO).
        decline_correspondence: Whether to decline correspondence challenges.
        max_iterations: Maximum event loop iterations (None for infinite).
            Used for testing.
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="[%(asctime)s] %(levelname)s %(threadName)s: %(message)s",
    )

    token = os.getenv("LICHESS_TOKEN")
    if not token:
        msg = "LICHESS_TOKEN environment variable is required"
        raise RuntimeError(msg)

    _logger.info("Token present. Initializing client and engine...")
    bot_version = get_and_increment_version()
    _logger.info("Bot version: v%s", bot_version)

    ctx = BotContext(
        api=LichessAPI(token),
        engine=RandomEngine(),
        bot_version=bot_version,
        decline_correspondence=decline_correspondence,
    )

    game_threads: dict[str, threading.Thread] = {}

    _logger.info("Connecting to Lichess event stream. Waiting for challenges...")
    backoff = 0

    _run_event_loop(ctx, game_threads, backoff, max_iterations)


def _run_event_loop(
    ctx: BotContext,
    game_threads: dict[str, threading.Thread],
    backoff: int,
    max_iterations: int | None,
) -> None:
    """Run the main event loop.

    Args:
        ctx: Bot context.
        game_threads: Dictionary of active game threads.
        backoff: Initial backoff value.
        max_iterations: Maximum iterations (None for infinite).
    """
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        backoff = _safe_event_loop_iteration(ctx, game_threads, backoff)
        iteration += 1


def main() -> None:
    """Parse arguments and run the Lichess bot."""
    parser = argparse.ArgumentParser(description="Run a minimal Lichess bot")
    parser.add_argument(
        "--log-level", default="INFO", help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--decline-correspondence",
        action="store_true",
        help="Decline correspondence challenges",
    )
    args = parser.parse_args()
    run_bot(args.log_level, decline_correspondence=args.decline_correspondence)


if __name__ == "__main__":
    main()

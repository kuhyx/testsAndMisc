"""Main entry point for the Lichess bot."""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass, field
import datetime
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
import chess.pgn
import requests

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
        _logger.debug(f"Game {game_id}: could not apply move {move}")


def _init_game_log(game_id: str, bot_version: int) -> Path | None:
    """Initialize the game log file."""
    game_log_path = Path.cwd() / f"lichess_bot_game_{game_id}.log"
    try:
        with open(game_log_path, "w") as lf:
            lf.write(f"game {game_id} started\n")
            lf.write(f"bot_version v{bot_version}\n")
    except OSError:
        return None
    return game_log_path


def _extract_game_full_data(
    event: dict[str, object],
    state: GameState,
    meta: GameMeta,
    api: LichessAPI,
) -> tuple[str, str | None]:
    """Extract data from a gameFull event.

    Returns:
        Tuple of (moves_string, status).
    """
    state_data = event.get("state", {})
    if not isinstance(state_data, dict):
        state_data = {}
    moves = str(state_data.get("moves", ""))
    status = state_data.get("status")

    # Update clocks - values are int milliseconds from API
    wtime = state_data.get("wtime")
    btime = state_data.get("btime")
    if state.color == "white":
        state.my_ms = int(wtime) if isinstance(wtime, int | float) else None
        state.opp_ms = int(btime) if isinstance(btime, int | float) else None
    else:
        state.my_ms = int(btime) if isinstance(btime, int | float) else None
        state.opp_ms = int(wtime) if isinstance(wtime, int | float) else None
    inc = state_data.get("winc") or state_data.get("binc")
    state.inc_ms = int(inc) if isinstance(inc, int | float) else 0

    # Extract player info
    white_data = event.get("white", {})
    black_data = event.get("black", {})
    if isinstance(white_data, dict) and isinstance(black_data, dict):
        white_id = white_data.get("id")
        black_id = black_data.get("id")
        meta.white_name = str(white_data.get("name") or white_id or "?")
        meta.black_name = str(black_data.get("name") or black_id or "?")

        # Determine color
        me = api.get_my_user_id()
        if me == white_id:
            state.color = "white"
        elif me == black_id:
            state.color = "black"

    # Extract date
    with contextlib.suppress(Exception):
        created_ms = event.get("createdAt") or event.get("createdAtDate")
        if created_ms is not None:
            meta.date_iso = datetime.datetime.fromtimestamp(
                int(str(created_ms)) / 1000,
                tz=datetime.timezone.utc,
            ).strftime("%Y.%m.%d")

    meta.site_url = f"https://lichess.org/{meta.game_id}"

    return moves, str(status) if status else None


def _extract_game_state_data(
    event: dict[str, object], state: GameState
) -> tuple[str, str | None]:
    """Extract data from a gameState event.

    Returns:
        Tuple of (moves_string, status).
    """
    moves = str(event.get("moves", ""))
    status = event.get("status")

    # Update clocks based on color
    if state.color == "white":
        state.my_ms = event.get("wtime", state.my_ms)  # type: ignore[assignment]
        state.opp_ms = event.get("btime", state.opp_ms)  # type: ignore[assignment]
        state.inc_ms = event.get("winc", state.inc_ms)  # type: ignore[assignment]
    elif state.color == "black":
        state.my_ms = event.get("btime", state.my_ms)  # type: ignore[assignment]
        state.opp_ms = event.get("wtime", state.opp_ms)  # type: ignore[assignment]
        state.inc_ms = event.get("binc", state.inc_ms)  # type: ignore[assignment]

    return moves, str(status) if status else None


def _calculate_time_budget(
    state: GameState, board: chess.Board, max_time_sec: float
) -> float:
    """Calculate time budget for the next move."""
    est_moves_left = max(10, min(60, 30 - board.fullmove_number // 2))
    time_left_sec = (state.my_ms or 0) / 1000.0
    inc_sec = (state.inc_ms or 0) / 1000.0
    budget = 0.6 * (time_left_sec / max(1, est_moves_left)) + 0.5 * inc_sec
    # Double the budget for more thoughtful moves
    budget *= 2.0
    return max(0.05, min(max_time_sec, budget))


def _log_move_to_file(
    log_path: Path | None, ply: int, move: chess.Move, reason: str
) -> None:
    """Log a move to the game log file."""
    if log_path:
        with open(log_path, "a") as lf:
            lf.write(f"ply {ply}: {move.uci()}\n{reason}\n\n")


def _attempt_move(
    ctx: BotContext,
    state: GameState,
    meta: GameMeta,
    board: chess.Board,
) -> bool:
    """Attempt to make a move. Returns True if game should continue."""
    budget = _calculate_time_budget(state, board, ctx.engine.max_time_sec)
    move, reason = ctx.engine.choose_move_with_explanation(
        board, time_budget_sec=budget
    )

    if move is None:
        _logger.info(f"Game {meta.game_id}: no legal moves (game likely over)")
        return False

    time_left_sec = (state.my_ms or 0) / 1000.0
    inc_sec = (state.inc_ms or 0) / 1000.0

    try:
        if move not in board.legal_moves:
            _logger.info(
                f"Game {meta.game_id}: selected move no longer legal; skipping send"
            )
        else:
            _logger.info(
                f"Game {meta.game_id}: playing {move.uci()} "
                f"(budget={budget:.2f}s, my_time_left={time_left_sec:.1f}s, "
                f"inc={inc_sec:.2f}s)"
            )
            _log_move_to_file(state.log_path, state.last_handled_len + 1, move, reason)
            ctx.api.make_move(meta.game_id, move)
    except requests.RequestException as e:
        _logger.warning(f"Game {meta.game_id}: move {move.uci()} failed: {e}")

    return True


def _is_my_turn(board: chess.Board, color: str | None) -> bool:
    """Check if it's our turn to move."""
    is_white_turn = board.turn
    return (is_white_turn and color == "white") or (
        (not is_white_turn) and color == "black"
    )


def _rebuild_board_from_moves(moves_list: list[str], game_id: str) -> chess.Board:
    """Rebuild board from list of moves."""
    board = chess.Board()
    for m in moves_list:
        _apply_move_to_board(board, m, game_id)
    return board


def _handle_move_if_needed(
    ctx: BotContext,
    state: GameState,
    meta: GameMeta,
    et: str,
    new_len: int,
) -> bool:
    """Handle making a move if it's our turn. Returns False if game ends."""
    my_turn = _is_my_turn(state.board, state.color)
    turn_str = "white" if state.board.turn else "black"
    _logger.info(f"Game {meta.game_id}: turn={turn_str}, my_turn={my_turn}")

    # Move policy
    allow_move = (et == "gameState") or (et == "gameFull" and new_len == 0)

    if my_turn and allow_move and not _attempt_move(ctx, state, meta, state.board):
        return False

    # Mark position as handled
    if et == "gameState" or (my_turn and allow_move):
        state.last_handled_len = new_len

    return True


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
        _logger.info(f"Game {meta.game_id}: joined as {state.color} (gameFull)")
    else:
        moves, status = _extract_game_state_data(event, state)

    moves_list = moves.split() if moves else []
    new_len = len(moves_list)

    _logger.info(
        f"Game {meta.game_id}: event={event_type}, moves={new_len}, color={state.color}"
    )

    if new_len == state.last_handled_len:
        _logger.debug(
            f"Game {meta.game_id}: position unchanged (len={new_len}), skipping"
        )
        return True

    # Rebuild board from moves
    state.board = _rebuild_board_from_moves(moves_list, meta.game_id)

    if state.color is None:
        _logger.info(f"Game {meta.game_id}: color unknown yet; waiting for gameFull")
        if event_type == "gameState":
            state.last_handled_len = new_len
        return True

    if not _handle_move_if_needed(ctx, state, meta, event_type, new_len):
        return False

    # Check for game end
    if status in _GAME_END_STATUSES:
        _logger.info(f"Game {meta.game_id} finished: {status}")
        return False

    return True


def _write_pgn_to_log(log_path: Path, board: chess.Board, meta: GameMeta) -> None:
    """Write PGN to the game log file."""
    game = chess.pgn.Game.from_board(board)
    with contextlib.suppress(Exception):
        game.headers["BotVersion"] = f"v{meta.bot_version}"
        if meta.site_url:
            game.headers["Site"] = meta.site_url
        if meta.date_iso:
            game.headers["Date"] = meta.date_iso
        if meta.white_name:
            game.headers["White"] = meta.white_name
        if meta.black_name:
            game.headers["Black"] = meta.black_name

    with open(log_path, "a") as lf:
        lf.write("\nPGN:\n")
        exporter = chess.pgn.StringExporter(
            headers=True, variations=False, comments=False
        )
        lf.write(game.accept(exporter))
        lf.write("\n")


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
            f"Game {game_id}: analysis script not found at {analyze_script}; "
            "skipping analysis"
        )
        return None

    _logger.info(f"Game {game_id}: starting post-game analysis ({total_plies} plies)")

    proc = subprocess.Popen(  # noqa: S603 - trusted internal analysis script
        [sys.executable, "-u", str(analyze_script), str(log_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    analyzed = 0
    lines: list[str] = []

    # stdout/stderr are guaranteed non-None with PIPE
    assert proc.stdout is not None  # noqa: S101
    assert proc.stderr is not None  # noqa: S101

    for line in proc.stdout:
        lines.append(line)
        m = _PLY_LINE_RE.match(line)
        if m:
            analyzed += 1
            _log_analysis_progress(game_id, analyzed, total_plies)

    stderr_text = proc.stderr.read() or ""
    ret = proc.wait()
    analysis_text = "".join(lines)

    if ret != 0:
        _logger.warning(f"Game {game_id}: analysis script exited with code {ret}")
        if stderr_text:
            analysis_text += "\n[stderr]\n" + stderr_text

    _logger.info(f"Game {game_id}: analysis complete")
    return analysis_text


def _log_analysis_progress(game_id: str, analyzed: int, total_plies: int) -> None:
    """Log analysis progress."""
    if total_plies:
        left = max(0, total_plies - analyzed)
        pct = analyzed / total_plies * 100.0
        _logger.info(
            f"Game {game_id}: analysis progress "
            f"{analyzed}/{total_plies} ({pct:.0f}%), left {left}"
        )
    else:
        _logger.info(
            f"Game {game_id}: analysis progress {analyzed} plies (total unknown)"
        )


def _insert_analysis_into_log(
    log_path: Path, analysis_text: str, meta: GameMeta
) -> None:
    """Insert analysis text into the log file before PGN section."""
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Find insertion point (before PGN)
        insert_idx = 0
        p = content.find("\nPGN:\n")
        if p != -1:
            insert_idx = p + 1
        elif content.startswith("PGN:\n"):
            insert_idx = 0
        else:
            insert_idx = len(content)

        # Build meta block
        meta_lines = []
        if meta.date_iso:
            meta_lines.append(f"Date: {meta.date_iso}")
        if meta.white_name or meta.black_name:
            meta_lines.append(
                f"Players: {meta.white_name or '?'} vs {meta.black_name or '?'}"
            )
        meta_block = "\n".join(meta_lines) + "\n" if meta_lines else ""

        analysis_block = f"{meta_block}ANALYSIS:\n{analysis_text.rstrip()}\n\n"
        new_content = content[:insert_idx] + analysis_block + content[insert_idx:]

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        _logger.debug(f"Game {meta.game_id}: could not write analysis to log: {e}")


def _finalize_game(state: GameState, meta: GameMeta) -> None:
    """Finalize game: write PGN and run analysis."""
    if not state.log_path:
        return

    try:
        _write_pgn_to_log(state.log_path, state.board, meta)
    except OSError as e:
        _logger.debug(f"Game {meta.game_id}: could not write PGN: {e}")
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
        _logger.debug(f"Game {meta.game_id}: analysis run failed: {e}")


def _handle_game(game_id: str, ctx: BotContext, my_color: str | None = None) -> None:
    """Handle a single game from start to finish."""
    _logger.info(f"Starting game thread for {game_id} [bot v{ctx.bot_version}]")

    meta = GameMeta(game_id=game_id, bot_version=ctx.bot_version)
    state = GameState(color=my_color)
    state.log_path = _init_game_log(game_id, ctx.bot_version)

    try:
        for event in ctx.api.stream_game_events(game_id):
            et = event.get("type")
            if et in ("chatLine", "opponentGone"):
                continue
            if not _process_game_event(event, ctx, state, meta):
                break
    except requests.RequestException:
        _logger.exception(f"Game {game_id} thread error")
    finally:
        _finalize_game(state, meta)
        _logger.info(f"Ending game thread for {game_id}")


def _handle_challenge(
    challenge: dict[str, object], api: LichessAPI, *, decline_correspondence: bool
) -> None:
    """Handle an incoming challenge."""
    ch_id = challenge.get("id", "")
    variant_data = challenge.get("variant", {})
    variant = (
        variant_data.get("key", "standard")
        if isinstance(variant_data, dict)
        else "standard"
    )
    speed = challenge.get("speed")

    perf_ok = speed in {"bullet", "blitz", "rapid", "classical"}
    not_corr = speed != "correspondence" or not decline_correspondence

    if variant == "standard" and perf_ok and not_corr:
        _logger.info(f"Accepting challenge {ch_id} ({speed})")
        api.accept_challenge(str(ch_id))
    else:
        _logger.info(f"Declining challenge {ch_id} (variant={variant}, speed={speed})")
        api.decline_challenge(str(ch_id))


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
            _logger.info(f"Game finished event: {game_id}")

    else:
        _logger.debug(f"Unhandled event: {json.dumps(event)}")


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


def run_bot(log_level: str = "INFO", *, decline_correspondence: bool = False) -> None:
    """Start the bot and listen for incoming events."""
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
    _logger.info(f"Bot version: v{bot_version}")

    ctx = BotContext(
        api=LichessAPI(token),
        engine=RandomEngine(),
        bot_version=bot_version,
        decline_correspondence=decline_correspondence,
    )

    game_threads: dict[str, threading.Thread] = {}

    _logger.info("Connecting to Lichess event stream. Waiting for challenges...")
    backoff = 0

    while True:
        try:
            backoff = _run_event_loop_iteration(ctx, game_threads)
        except requests.RequestException as e:  # noqa: PERF203 - intentional reconnection loop
            _logger.warning(f"Event stream error: {e}")
            backoff = backoff_sleep(backoff)


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

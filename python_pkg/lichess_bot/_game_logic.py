"""Game logic and challenge handling helpers for the Lichess bot."""

from __future__ import annotations

import contextlib
import datetime
import logging
from typing import TYPE_CHECKING

import chess
import chess.pgn
import requests

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.lichess_bot.lichess_api import LichessAPI
    from python_pkg.lichess_bot.main import BotContext, GameMeta, GameState

_logger = logging.getLogger(__name__)


def _update_clocks_from_state(state_data: dict[str, object], state: GameState) -> None:
    """Update clock values from state data."""
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


def _extract_player_info(
    event: dict[str, object], state: GameState, meta: GameMeta, api: LichessAPI
) -> None:
    """Extract player info and determine color."""
    white_data = event.get("white", {})
    black_data = event.get("black", {})
    if not isinstance(white_data, dict) or not isinstance(black_data, dict):
        return
    white_id = white_data.get("id")
    black_id = black_data.get("id")
    meta.white_name = str(white_data.get("name") or white_id or "?")
    meta.black_name = str(black_data.get("name") or black_id or "?")
    me = api.get_my_user_id()
    if me == white_id:
        state.color = "white"
    elif me == black_id:
        state.color = "black"


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

    _update_clocks_from_state(state_data, state)
    _extract_player_info(event, state, meta, api)

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
        state.my_ms = event.get("wtime", state.my_ms)
        state.opp_ms = event.get("btime", state.opp_ms)
        state.inc_ms = event.get("winc", state.inc_ms)
    elif state.color == "black":
        state.my_ms = event.get("btime", state.my_ms)
        state.opp_ms = event.get("wtime", state.opp_ms)
        state.inc_ms = event.get("binc", state.inc_ms)

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
        with log_path.open("a") as lf:
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
        _logger.info("Game %s: no legal moves (game likely over)", meta.game_id)
        return False

    time_left_sec = (state.my_ms or 0) / 1000.0
    inc_sec = (state.inc_ms or 0) / 1000.0

    try:
        if move not in board.legal_moves:
            _logger.info(
                "Game %s: selected move no longer legal; skipping send", meta.game_id
            )
        else:
            _logger.info(
                "Game %s: playing %s (budget=%.2fs, my_time_left=%.1fs, inc=%.2fs)",
                meta.game_id,
                move.uci(),
                budget,
                time_left_sec,
                inc_sec,
            )
            _log_move_to_file(state.log_path, state.last_handled_len + 1, move, reason)
            ctx.api.make_move(meta.game_id, move)
    except requests.RequestException as e:
        _logger.warning("Game %s: move %s failed: %s", meta.game_id, move.uci(), e)

    return True


def _is_my_turn(board: chess.Board, color: str | None) -> bool:
    """Check if it's our turn to move."""
    is_white_turn = board.turn
    return (is_white_turn and color == "white") or (
        (not is_white_turn) and color == "black"
    )


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
    _logger.info("Game %s: turn=%s, my_turn=%s", meta.game_id, turn_str, my_turn)

    # Move policy
    allow_move = (et == "gameState") or (et == "gameFull" and not new_len)

    if my_turn and allow_move and not _attempt_move(ctx, state, meta, state.board):
        return False

    # Mark position as handled
    if et == "gameState" or (my_turn and allow_move):
        state.last_handled_len = new_len

    return True


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
        _logger.info("Accepting challenge %s (%s)", ch_id, speed)
        api.accept_challenge(str(ch_id))
    else:
        _logger.info(
            "Declining challenge %s (variant=%s, speed=%s)", ch_id, variant, speed
        )
        api.decline_challenge(str(ch_id))


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

    with log_path.open("a") as lf:
        lf.write("\nPGN:\n")
        exporter = chess.pgn.StringExporter(
            headers=True, variations=False, comments=False
        )
        lf.write(game.accept(exporter))
        lf.write("\n")


def _insert_analysis_into_log(
    log_path: Path, analysis_text: str, meta: GameMeta
) -> None:
    """Insert analysis text into the log file before PGN section."""
    try:
        with log_path.open(encoding="utf-8", errors="replace") as f:
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

        with log_path.open("w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        _logger.debug("Game %s: could not write analysis to log: %s", meta.game_id, e)

import argparse
import json
import logging
import os
import threading
import time
from typing import Optional

import chess
import chess.pgn

from .engine import RandomEngine
from .lichess_api import LichessAPI
from .utils import backoff_sleep


def run_bot(log_level: str = "INFO", decline_correspondence: bool = False) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="[%(asctime)s] %(levelname)s %(threadName)s: %(message)s",
    )

    token = os.getenv("LICHESS_TOKEN")
    if not token:
        raise RuntimeError("LICHESS_TOKEN environment variable is required")

    logging.info("Token present. Initializing client and engine...")
    api = LichessAPI(token)
    engine = RandomEngine()

    game_threads = {}

    def handle_game(game_id: str, my_color: Optional[str] = None):
        logging.info(f"Starting game thread for {game_id}")
        board = chess.Board()
        color: Optional[str] = my_color
        # Track how many moves we have already processed; start at -1 so we act on the first state (0 moves)
        last_handled_len = -1
        # Prepare a per-game log file
        game_log_path = os.path.join(os.getcwd(), f"lichess_bot_game_{game_id}.log")
        try:
            with open(game_log_path, "w") as lf:
                lf.write(f"game {game_id} started\n")
        except Exception:
            game_log_path = None
        # Simple time manager state
        my_ms = None
        opp_ms = None
        inc_ms = 0
        try:
            for event in api.stream_game_events(game_id):
                et = event.get("type")
                if et in ("gameFull", "gameState"):
                    # Determine moves list and optional status
                    if et == "gameFull":
                        state = event.get("state", {})
                        moves = state.get("moves", "")
                        status = state.get("status")
                        # clocks are in milliseconds if present
                        my_ms = state.get("wtime") if color == "white" else state.get("btime")
                        opp_ms = state.get("btime") if color == "white" else state.get("wtime")
                        inc_ms = state.get("winc") or state.get("binc") or 0
                        # Discover my color from gameFull
                        white_id = event["white"].get("id")
                        black_id = event["black"].get("id")
                        me = api.get_my_user_id()
                        if me == white_id:
                            color = "white"
                        elif me == black_id:
                            color = "black"
                        logging.info(f"Game {game_id}: joined as {color} (gameFull)")
                    else:
                        moves = event.get("moves", "")
                        status = event.get("status")
                        # update clocks from gameState if present
                        if color == "white":
                            my_ms = event.get("wtime", my_ms)
                            opp_ms = event.get("btime", opp_ms)
                            inc_ms = event.get("winc", inc_ms)
                        elif color == "black":
                            my_ms = event.get("btime", my_ms)
                            opp_ms = event.get("wtime", opp_ms)
                            inc_ms = event.get("binc", inc_ms)

                    moves_list = moves.split() if moves else []
                    new_len = len(moves_list)
                    logging.info(
                        f"Game {game_id}: event={et}, moves={new_len}, color={color}"
                    )
                    if new_len == last_handled_len:
                        logging.debug(f"Game {game_id}: position unchanged (len={new_len}), skipping")
                        continue

                    # Rebuild board from moves
                    board = chess.Board()
                    for m in moves_list:
                        try:
                            board.push_uci(m)
                        except Exception:
                            logging.debug(f"Game {game_id}: could not apply move {m}")

                    if color is None:
                        logging.info(f"Game {game_id}: color unknown yet; waiting for gameFull")
                        last_handled_len = new_len
                        continue

                    is_white_turn = board.turn
                    my_turn = (is_white_turn and color == "white") or ((not is_white_turn) and color == "black")
                    logging.info(
                        f"Game {game_id}: turn={'white' if is_white_turn else 'black'}, my_turn={my_turn}"
                    )
                    if my_turn:
                        # Compute a per-move time budget (seconds) based on remaining time
                        # Heuristic: use min( max_time_sec, max(0.05, 0.6 * my_time_left/remaining_moves + inc) )
                        # Estimate remaining moves as 30 - ply/2 bounded to [10, 60]
                        est_moves_left = max(10, min(60, 30 - board.fullmove_number // 2))
                        time_left_sec = (my_ms or 0) / 1000.0
                        inc_sec = (inc_ms or 0) / 1000.0
                        budget = 0.6 * (time_left_sec / max(1, est_moves_left)) + 0.5 * inc_sec
                        # Spend more time per move (requested): double the budget
                        budget *= 2.0
                        # Keep within reasonable bounds
                        budget = max(0.05, min(engine.max_time_sec, budget))
                        move, reason = engine.choose_move_with_explanation(board, time_budget_sec=budget)
                        if move is None:
                            logging.info(f"Game {game_id}: no legal moves (game likely over)")
                            break
                        try:
                            logging.info(f"Game {game_id}: playing {move.uci()} (budget={budget:.2f}s, my_time_left={time_left_sec:.1f}s, inc={inc_sec:.2f}s)")
                            if game_log_path:
                                with open(game_log_path, "a") as lf:
                                    lf.write(f"ply {last_handled_len+1}: {move.uci()}\n{reason}\n\n")
                            api.make_move(game_id, move)
                        except Exception as e:
                            logging.warning(f"Game {game_id}: move {move.uci()} failed: {e}")
                    # Mark this position as handled (whether or not we moved)
                    last_handled_len = new_len
                    if status in {"mate", "resign", "stalemate", "timeout", "draw"}:
                        logging.info(f"Game {game_id} finished: {status}")
                        break
                elif et == "chatLine":
                    continue
                elif et == "opponentGone":
                    continue
        except Exception as e:
            logging.exception(f"Game {game_id} thread error: {e}")
        finally:
            # On game end, write full PGN to the log file
            try:
                if game_log_path:
                    game = chess.pgn.Game.from_board(board)
                    with open(game_log_path, "a") as lf:
                        lf.write("\nPGN:\n")
                        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
                        lf.write(game.accept(exporter))
                        lf.write("\n")
            except Exception as e:
                logging.debug(f"Game {game_id}: could not write PGN: {e}")
            logging.info(f"Ending game thread for {game_id}")

    # Main event stream: challenge and game start events
    logging.info("Connecting to Lichess event stream. Waiting for challenges...")
    backoff = 0
    while True:
        try:
            for event in api.stream_events():
                if event.get("type") == "challenge":
                    challenge = event["challenge"]
                    ch_id = challenge["id"]
                    variant = challenge.get("variant", {}).get("key", "standard")
                    speed = challenge.get("speed")
                    perf_ok = speed in {"bullet", "blitz", "rapid", "classical"}
                    not_corr = challenge.get("speed") != "correspondence" or not decline_correspondence
                    if variant == "standard" and perf_ok and not_corr:
                        logging.info(f"Accepting challenge {ch_id} ({speed})")
                        api.accept_challenge(ch_id)
                    else:
                        logging.info(f"Declining challenge {ch_id} (variant={variant}, speed={speed})")
                        api.decline_challenge(ch_id)

                elif event.get("type") == "gameStart":
                    game_id = event["game"]["id"]
                    # Spin up a game thread
                    if game_id not in game_threads or not game_threads[game_id].is_alive():
                        t = threading.Thread(target=handle_game, args=(game_id,), name=f"game-{game_id}")
                        t.daemon = True
                        game_threads[game_id] = t
                        t.start()

                elif event.get("type") == "gameFinish":
                    game_id = event["game"]["id"]
                    logging.info(f"Game finished event: {game_id}")
                else:
                    logging.debug(f"Unhandled event: {json.dumps(event)}")
            # If stream ends normally, reset backoff
            backoff = 0
        except Exception as e:
            logging.warning(f"Event stream error: {e}")
            backoff = backoff_sleep(backoff)


def main():
    parser = argparse.ArgumentParser(description="Run a minimal Lichess bot")
    parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    parser.add_argument("--decline-correspondence", action="store_true", help="Decline correspondence challenges")
    args = parser.parse_args()
    run_bot(args.log_level, args.decline_correspondence)


if __name__ == "__main__":
    main()

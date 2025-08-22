import argparse
import json
import logging
import os
import threading
import time
from typing import Optional

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
        try:
            board, color = api.join_game_stream(game_id, my_color)
            logging.info(f"Game {game_id}: joined as {color}")

            while True:
                # If it's our turn, pick and play a move
                if (board.turn and color == "white") or (not board.turn and color == "black"):
                    move = engine.choose_move(board)
                    if move is None:
                        logging.info(f"Game {game_id}: no legal moves (game likely over)")
                        break
                    api.make_move(game_id, move)
                # Sleep briefly to avoid hammering the API
                time.sleep(0.2)

                # Poll for updates to keep board in sync
                updates = api.get_game_state(game_id)
                if updates is None:
                    continue
                # Apply last move if present
                last_move_uci = updates.get("lastMove")
                if last_move_uci:
                    try:
                        board.push_uci(last_move_uci)
                    except Exception:
                        # It may already be applied; ignore
                        pass

                # Check for game end
                if updates.get("status") in {"mate", "resign", "stalemate", "timeout", "draw"}:
                    logging.info(f"Game {game_id} finished: {updates.get('status')}")
                    break
        except Exception as e:
            logging.exception(f"Game {game_id} thread error: {e}")
        finally:
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

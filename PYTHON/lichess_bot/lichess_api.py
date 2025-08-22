import json
import logging
import time
from typing import Dict, Generator, Optional, Tuple

import requests
import chess


LICHESS_API = "https://lichess.org"


class LichessAPI:
    def __init__(self, token: str, session: Optional[requests.Session] = None):
        self.token = token
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "minimal-lichess-bot/0.1 (+https://lichess.org)"
        })

    def stream_events(self) -> Generator[Dict, None, None]:
        url = f"{LICHESS_API}/api/stream/event"
        with self.session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logging.debug(f"Skipping non-JSON line: {line}")

    def accept_challenge(self, challenge_id: str) -> None:
        url = f"{LICHESS_API}/api/challenge/{challenge_id}/accept"
        r = self.session.post(url, timeout=30)
        r.raise_for_status()

    def decline_challenge(self, challenge_id: str, reason: str = "generic") -> None:
        url = f"{LICHESS_API}/api/challenge/{challenge_id}/decline"
        data = {"reason": reason}
        r = self.session.post(url, data=data, timeout=30)
        r.raise_for_status()

    def join_game_stream(self, game_id: str, my_color: Optional[str]) -> Tuple[chess.Board, str]:
        # Join board stream once to detect initial state and my color
        url = f"{LICHESS_API}/api/board/game/stream/{game_id}"
        board = chess.Board()
        color = my_color or "white"

        with self.session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                t = event.get("type")
                if t == "gameFull":
                    # set my color
                    white_id = event["white"].get("id")
                    black_id = event["black"].get("id")
                    me = self.get_my_user_id()
                    if me == white_id:
                        color = "white"
                    elif me == black_id:
                        color = "black"

                    # Load initial state
                    state = event.get("state", {})
                    moves = state.get("moves", "")
                    if moves:
                        for m in moves.split():
                            try:
                                board.push_uci(m)
                            except Exception:
                                pass
                    break
                elif t == "gameState":
                    # may see gameState first in rare cases; skip until gameFull
                    continue
        return board, color

    def make_move(self, game_id: str, move: chess.Move) -> None:
        url = f"{LICHESS_API}/api/board/game/{game_id}/move/{move.uci()}"
        r = self.session.post(url, timeout=30)
        if r.status_code == 429:
            time.sleep(0.5)
            r = self.session.post(url, timeout=30)
        r.raise_for_status()

    def get_game_state(self, game_id: str) -> Optional[Dict]:
        url = f"{LICHESS_API}/api/board/game/stream/{game_id}"
        # Use a short-lived request to read a single line update
        with self.session.get(url, stream=True, timeout=10) as r:
            if r.status_code >= 400:
                return None
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "gameState":
                    return event
                if event.get("type") == "gameFull":
                    return event.get("state")
                # If we get other events, keep looping; this request is short-lived anyway.
        return None

    def get_my_user_id(self) -> Optional[str]:
        url = f"{LICHESS_API}/api/account"
        r = self.session.get(url, timeout=30)
        if r.status_code == 200:
            return r.json().get("id")
        return None

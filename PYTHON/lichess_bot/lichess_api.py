from collections.abc import Generator
import json
import logging
import time

import chess
import requests

LICHESS_API = "https://lichess.org"


class LichessAPI:
    def __init__(self, token: str, session: requests.Session | None = None):
        self.token = token
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": "minimal-lichess-bot/0.1 (+https://lichess.org)",
            }
        )

    def _request(
        self, method: str, url: str, *, raise_for_status: bool = False, **kwargs
    ) -> requests.Response:
        """Wrapper around session.request that logs every request/response.

        - Logs start (method+URL) and end (status, elapsed).
        - On 4xx/5xx, logs a warning with a small snippet of the response body.
        - Optionally raises for status.
        """
        t0 = time.monotonic()
        logging.info(f"HTTP {method} {url} -> sending")
        try:
            r = self.session.request(method, url, **kwargs)
        except Exception as e:
            logging.exception(f"HTTP {method} {url} -> exception: {e}")
            raise
        elapsed = time.monotonic() - t0
        status = r.status_code
        if status >= 400:
            # Log a brief error body snippet if available
            snippet = None
            try:
                text = r.text or ""
                snippet = text[:200].replace("\n", " ")
            except Exception:
                snippet = None
            if snippet:
                logging.warning(
                    f"HTTP {method} {url} -> {status} in {elapsed:.2f}s body='{snippet}'"
                )
            else:
                logging.warning(f"HTTP {method} {url} -> {status} in {elapsed:.2f}s")
        else:
            logging.info(f"HTTP {method} {url} -> {status} in {elapsed:.2f}s")
        if raise_for_status:
            r.raise_for_status()
        return r

    def stream_events(self) -> Generator[dict, None, None]:
        url = f"{LICHESS_API}/api/stream/event"
        backoff = 0.5
        while True:
            try:
                # Use NDJSON Accept and no timeout for long-lived stream
                headers = {"Accept": "application/x-ndjson"}
                with self._request(
                    "GET", url, headers=headers, stream=True, timeout=None
                ) as r:
                    r.raise_for_status()
                    backoff = 0.5  # reset on success
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            logging.debug(f"Skipping non-JSON line: {line}")
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status == 429:
                    logging.warning("Event stream hit 429; backing off")
                    time.sleep(backoff)
                    backoff = min(8.0, backoff * 2)
                    continue
                raise

    def accept_challenge(self, challenge_id: str) -> None:
        url = f"{LICHESS_API}/api/challenge/{challenge_id}/accept"
        self._request("POST", url, timeout=30, raise_for_status=True)

    def decline_challenge(self, challenge_id: str, reason: str = "generic") -> None:
        url = f"{LICHESS_API}/api/challenge/{challenge_id}/decline"
        data = {"reason": reason}
        self._request("POST", url, data=data, timeout=30, raise_for_status=True)

    def join_game_stream(
        self, game_id: str, my_color: str | None
    ) -> tuple[chess.Board, str]:
        """Deprecated: use stream_game_events and parse initial state there."""
        # Fallback to initial behavior for compatibility
        url = f"{LICHESS_API}/api/board/game/stream/{game_id}"
        board = chess.Board()
        color = my_color or "white"
        headers = {"Accept": "application/x-ndjson"}
        with self._request("GET", url, headers=headers, stream=True, timeout=None) as r:
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
                    white_id = event["white"].get("id")
                    black_id = event["black"].get("id")
                    me = self.get_my_user_id()
                    if me == white_id:
                        color = "white"
                    elif me == black_id:
                        color = "black"
                    state = event.get("state", {})
                    moves = state.get("moves", "")
                    if moves:
                        for m in moves.split():
                            try:
                                board.push_uci(m)
                            except Exception:
                                pass
                    break
        return board, color

    def stream_game_events(self, game_id: str) -> Generator[dict, None, None]:
        url = f"{LICHESS_API}/api/board/game/stream/{game_id}"
        headers = {"Accept": "application/x-ndjson"}
        with self._request("GET", url, headers=headers, stream=True, timeout=None) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logging.debug(f"Skipping non-JSON line in game {game_id}: {line}")

    def make_move(self, game_id: str, move: chess.Move) -> None:
        url = f"{LICHESS_API}/api/board/game/{game_id}/move/{move.uci()}"
        r = self._request("POST", url, timeout=30)
        if r.status_code in (400, 409):
            # Likely not our turn or move already played; do not retry to avoid spam
            r.raise_for_status()
            return
        if r.status_code == 429:
            logging.warning(f"HTTP POST {url} -> 429; retrying once after 0.5s")
            time.sleep(0.5)
            r = self._request("POST", url, timeout=30)
        r.raise_for_status()

    def get_game_state(self, game_id: str) -> dict | None:
        """Deprecated: use stream_game_events in a persistent loop."""
        return None

    def get_my_user_id(self) -> str | None:
        url = f"{LICHESS_API}/api/account"
        r = self._request("GET", url, timeout=30)
        if r.status_code == 200:
            return r.json().get("id")
        return None

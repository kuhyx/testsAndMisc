"""Lichess API client for bot interactions."""

from collections.abc import Generator  # pylint: disable=import-error
import contextlib
from http import HTTPStatus
import json
import logging
import time

import chess
import requests

_logger = logging.getLogger(__name__)

LICHESS_API = "https://lichess.org"


class LichessAPI:
    """Client for interacting with the Lichess Bot API."""

    def __init__(self, token: str, session: requests.Session | None = None) -> None:
        """Initialize the API client with authentication token."""
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
        self,
        method: str,
        url: str,
        *,
        raise_for_status: bool = False,
        **kwargs: object,
    ) -> requests.Response:
        """Wrapper around session.request that logs every request/response.

        - Logs start (method+URL) and end (status, elapsed).
        - On 4xx/5xx, logs a warning with a small snippet of the response body.
        - Optionally raises for status.
        """
        t0 = time.monotonic()
        _logger.info("HTTP %s %s -> sending", method, url)
        try:
            r = self.session.request(method, url, **kwargs)  # type: ignore[arg-type]
        except Exception:
            _logger.exception("HTTP %s %s -> exception", method, url)
            raise
        elapsed = time.monotonic() - t0
        status = r.status_code
        if status >= HTTPStatus.BAD_REQUEST:
            # Log a brief error body snippet if available
            snippet = None
            try:
                text = r.text or ""
                snippet = text[:200].replace("\n", " ")
            except (AttributeError, TypeError):
                snippet = None
            if snippet:
                _logger.warning(
                    "HTTP %s %s -> %s in %.2fs body='%s'",
                    method,
                    url,
                    status,
                    elapsed,
                    snippet,
                )
            else:
                _logger.warning(
                    "HTTP %s %s -> %s in %.2fs", method, url, status, elapsed
                )
        else:
            _logger.info("HTTP %s %s -> %s in %.2fs", method, url, status, elapsed)
        if raise_for_status:
            r.raise_for_status()
        return r

    def stream_events(self) -> Generator[dict, None, None]:
        """Stream incoming events (challenges, game starts, etc.)."""
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
                            _logger.debug("Skipping non-JSON line: %s", line)
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status == HTTPStatus.TOO_MANY_REQUESTS:
                    _logger.warning("Event stream hit 429; backing off")
                    time.sleep(backoff)
                    backoff = min(8.0, backoff * 2)
                    continue
                raise

    def accept_challenge(self, challenge_id: str) -> None:
        """Accept a challenge by its ID."""
        url = f"{LICHESS_API}/api/challenge/{challenge_id}/accept"
        self._request("POST", url, timeout=30, raise_for_status=True)

    def decline_challenge(self, challenge_id: str, reason: str = "generic") -> None:
        """Decline a challenge with an optional reason."""
        url = f"{LICHESS_API}/api/challenge/{challenge_id}/decline"
        data = {"reason": reason}
        self._request("POST", url, data=data, timeout=30, raise_for_status=True)

    def _parse_game_full_event(
        self, event: dict, board: chess.Board, color: str
    ) -> str:
        """Parse gameFull event and update board. Returns determined color."""
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
                with contextlib.suppress(Exception):
                    board.push_uci(m)
        return color

    def join_game_stream(
        self, game_id: str, my_color: str | None
    ) -> tuple[chess.Board, str]:
        """Deprecated: use stream_game_events and parse initial state there."""
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
                if event.get("type") == "gameFull":
                    color = self._parse_game_full_event(event, board, color)
                    break
        return board, color

    def stream_game_events(self, game_id: str) -> Generator[dict, None, None]:
        """Stream game state events for a specific game."""
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
                    _logger.debug(
                        "Skipping non-JSON line in game %s: %s", game_id, line
                    )

    def make_move(self, game_id: str, move: chess.Move) -> None:
        """Submit a move to an active game."""
        url = f"{LICHESS_API}/api/board/game/{game_id}/move/{move.uci()}"
        r = self._request("POST", url, timeout=30)
        if r.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.CONFLICT):
            # Likely not our turn or move already played; do not retry to avoid spam
            r.raise_for_status()
            return
        if r.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            _logger.warning("HTTP POST %s -> 429; retrying once after 0.5s", url)
            time.sleep(0.5)
            r = self._request("POST", url, timeout=30)
        r.raise_for_status()

    def get_game_state(self, _game_id: str) -> dict | None:
        """Deprecated: use stream_game_events in a persistent loop."""
        return None

    def get_my_user_id(self) -> str | None:
        """Fetch the authenticated user's ID."""
        url = f"{LICHESS_API}/api/account"
        r = self._request("GET", url, timeout=30)
        if r.status_code == HTTPStatus.OK:
            return r.json().get("id")
        return None

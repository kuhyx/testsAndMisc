"""Endurain API client for activity uploads.

Endurain does not deduplicate uploads, so the distinction between "definitely
rejected" and "might have been committed" decides whether a retry is safe:

  * 4xx  -- the server refused the file. Retrying is pointless but harmless;
            the file is routed to Endurain's bulk_import for manual recovery.
  * 5xx / timeout / connection loss -- the server may have created the activity
            before the response was lost. Retrying blindly would duplicate it,
            so the file is left in the inbox and reported as AMBIGUOUS. The
            caller must not treat this as either success or a clean failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import TYPE_CHECKING, Any, Protocol

import requests

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)

UPLOAD_PATH = "/api/v1/activities/create/upload"
# Endurain exposes no "does this run exist" query, so existence is decided by
# fetching a recent page and comparing start times client-side.
RECENT_PATH = "/api/v1/activities/user/{user_id}/page_number/1/num_records/{n}"
_RECENT_RECORDS = 50
# Start times are compared with a tolerance because the recorded value is not
# the one in the file: a run whose export embeds 21:51:04Z was stored by
# Endurain as 21:51:05Z. Two genuinely distinct runs starting inside two
# minutes of each other is not a real scenario, so the window is generous.
_START_TOLERANCE_SECONDS = 120
# The API key goes in X-API-Key. Endurain's own OpenAPI schema declares the
# APIKeyHeader security scheme as name "X-Client-Type", which is wrong --
# verified against the running server: X-API-Key with a bad key returns
# {"detail":"Invalid API key"} (parsed, then rejected), whereas X-Client-Type
# returns {"detail":"Not authenticated..."} (never read as a key at all).
_API_KEY_HEADER = "X-API-Key"
_TIMEOUT = 120
_HTTP_BAD_REQUEST = 400
_HTTP_SERVER_ERROR = 500


class SupportsUpload(Protocol):
    """The upload surface :func:`_process` needs.

    Declared structurally so tests can substitute a stub without subclassing
    the real client (and without mypy complaining about the swap).
    """

    def upload(self, path: Path) -> Result:
        """Upload one activity file and report what happened."""
        ...  # pragma: no cover - structural typing only, never executed

    def recent_start_times(self, user_id: int) -> list[datetime] | None:
        """Return recent activity start times, or None if unknowable."""
        ...  # pragma: no cover - structural typing only, never executed


class Outcome(Enum):
    """What happened to one upload attempt."""

    OK = "ok"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Result:
    """The outcome of a single upload attempt."""

    outcome: Outcome
    activity_id: int | None
    detail: str


class EndurainClient:
    """Minimal client for the endpoints this importer needs."""

    def __init__(self, base_url: str, api_key: str) -> None:
        """Build a client for ``base_url`` authenticating with ``api_key``."""
        self._base = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({_API_KEY_HEADER: api_key})

    def about(self) -> dict[str, Any]:
        """Liveness probe; raises on any non-2xx."""
        resp = self._session.get(f"{self._base}/api/v1/about", timeout=30)
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()
        return body

    def recent_start_times(self, user_id: int) -> list[datetime] | None:
        """Return start times of recent activities, or None if unknowable.

        None means "the question could not be answered" -- a transport failure,
        an auth failure, or a body that did not parse. It is deliberately not
        an empty list: callers must not read a failed lookup as "no matching
        activity exists" and upload on the strength of it.
        """
        url = f"{self._base}{RECENT_PATH}".format(user_id=user_id, n=_RECENT_RECORDS)
        try:
            resp = self._session.get(url, timeout=30)
        except requests.RequestException as exc:
            _logger.warning("could not list recent activities: %s", exc)
            return None
        if resp.status_code >= _HTTP_BAD_REQUEST:
            _logger.warning(
                "could not list recent activities: %s (the API key needs the "
                "activities:read scope for duplicate detection)",
                resp.status_code,
            )
            return None
        try:
            body = resp.json()
        except ValueError:
            _logger.warning("recent activities response was not JSON")
            return None
        if not isinstance(body, list):
            _logger.warning("recent activities response was not a list")
            return None
        return [
            parsed
            for item in body
            if isinstance(item, dict)
            and (parsed := _parse_start(item.get("start_time"))) is not None
        ]

    def upload(self, path: Path) -> Result:
        """Upload one activity file."""
        try:
            with path.open("rb") as handle:
                resp = self._session.post(
                    f"{self._base}{UPLOAD_PATH}",
                    files={"file": (path.name, handle)},
                    timeout=_TIMEOUT,
                )
        except requests.RequestException as exc:
            # The request may or may not have reached the server.
            return Result(Outcome.AMBIGUOUS, None, f"transport error: {exc}")

        if resp.status_code >= _HTTP_SERVER_ERROR:
            return Result(Outcome.AMBIGUOUS, None, f"server error {resp.status_code}")
        if resp.status_code >= _HTTP_BAD_REQUEST:
            return Result(
                Outcome.REJECTED,
                None,
                f"{resp.status_code}: {resp.text[:200]}",
            )
        return Result(Outcome.OK, _activity_id(resp), "uploaded")


def _activity_id(resp: requests.Response) -> int | None:
    """Best-effort extraction of the new activity id from a success body."""
    try:
        body = resp.json()
    except ValueError:
        return None
    if isinstance(body, int):
        return body
    if isinstance(body, dict):
        for key in ("id", "activity_id"):
            value = body.get(key)
            if isinstance(value, int):
                return value
    return None


def _parse_start(raw: object) -> datetime | None:
    """Parse an Endurain start_time into an aware UTC datetime."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Endurain returns local-offset timestamps; a naive value is read as UTC
    # so the comparison below never comes down to the reader's timezone.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def already_present(start: datetime, known: list[datetime]) -> bool:
    """True when ``start`` matches a known activity within the tolerance."""
    return any(
        abs((start - other).total_seconds()) <= _START_TOLERANCE_SECONDS
        for other in known
    )

"""Duplicate detection that reads Endurain's database directly.

Endurain's API keys cannot answer "what do you already hold": the key scope
allow-list is ``{"activities:upload"}`` (enforced twice, deliberately), and the
activities read route is mounted JWT-only, so a key fails at *authentication*
before any scope check. Verified against v0.19.0; upstream documents no plan to
widen it.

That leaves the database. The postgres container publishes no host port, so
this goes through ``docker exec`` rather than a TCP client -- no new dependency,
no compose change, and no port exposed to the host just to read four rows.

This is a *fallback*, not a replacement: :mod:`__main__` asks the HTTP API first
so that the supported path starts working by itself if Endurain ever grants the
scope.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import logging
import os
import subprocess
from typing import TYPE_CHECKING, Protocol

from python_pkg.endurain_import.upload import _parse_start

if TYPE_CHECKING:
    from datetime import datetime


class SupportsRecentStartTimes(Protocol):
    """The lookup surface :func:`known_start_times` needs from a client."""

    def recent_start_times(self, user_id: int) -> list[datetime] | None:
        """Return recent activity start times, or None if unknowable."""
        ...  # pragma: no cover - structural typing only, never executed


_logger = logging.getLogger(__name__)

_CONTAINER_ENV = "ENDURAIN_PG_CONTAINER"
_NO_DB_ENV = "ENDURAIN_NO_DB"
_DEFAULT_CONTAINER = "endurain-postgres"
_DB_USER = "endurain"
_DB_NAME = "endurain"
# Mirrors the HTTP path's page size so both backends answer the same question.
_RECENT_RECORDS = 50
_TIMEOUT = 30

# -At: tuples only, unaligned -- one bare timestamp per line, no header or
# padding to strip. The query goes in on stdin rather than via -c because psql
# only substitutes -v variables in scripts it reads, never inside -c; that
# keeps user_id out of the SQL string instead of formatting it in.
_QUERY = (
    "SELECT start_time FROM activities "
    "WHERE user_id = :uid ORDER BY start_time DESC LIMIT :lim;"
)

Runner = Callable[[Sequence[str], str], "subprocess.CompletedProcess[str]"]


def _run(argv: Sequence[str], stdin: str) -> subprocess.CompletedProcess[str]:
    """Execute ``argv``, feeding ``stdin``, and capture its output.

    Split out so tests can inject a stub: the real call is unreachable in a
    unit test, and the branches around its result are exactly what needs
    covering.
    """
    return subprocess.run(
        list(argv),
        input=stdin,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        check=False,
    )


class EndurainDatabase:
    """Reads recent activity start times straight out of postgres."""

    def __init__(self, container: str | None = None, runner: Runner = _run) -> None:
        """Build a reader for ``container``, executing through ``runner``."""
        self._container = container or os.environ.get(
            _CONTAINER_ENV, _DEFAULT_CONTAINER
        )
        self._run = runner

    def recent_start_times(self, user_id: int) -> list[datetime] | None:
        """Return recent activity start times, or None if unknowable.

        None means the question could not be answered -- the container is gone,
        psql failed, or the call timed out. An empty list is a real answer
        ("this user has no activities") and callers may act on it; None must
        only ever mean "fall back". Conflating the two would let a docker
        failure read as "nothing is stored" and re-upload everything.
        """
        argv = [
            "docker",
            "exec",
            "-i",
            self._container,
            "psql",
            "-U",
            _DB_USER,
            "-d",
            _DB_NAME,
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-v",
            f"uid={int(user_id)}",
            "-v",
            f"lim={_RECENT_RECORDS}",
        ]
        try:
            proc = self._run(argv, _QUERY)
        except (OSError, subprocess.SubprocessError) as exc:
            _logger.warning("could not read activities from the database: %s", exc)
            return None
        if proc.returncode != 0:
            _logger.warning(
                "could not read activities from the database: psql exited %s (%s)",
                proc.returncode,
                (proc.stderr or "").strip()[:200] or "no stderr",
            )
            return None
        return _parse_rows(proc.stdout)


def _parse_rows(stdout: str) -> list[datetime]:
    """Turn psql's one-timestamp-per-line output into datetimes.

    Unparsable lines are dropped rather than failing the lookup: a row this
    function cannot read is one fewer duplicate it can catch, which is the
    safe direction -- the ledger still guards the upload.
    """
    return [
        parsed
        for line in stdout.splitlines()
        if (stripped := line.strip()) and (parsed := _parse_start(stripped)) is not None
    ]


def known_start_times(
    client: SupportsRecentStartTimes, user_id: int
) -> list[datetime] | None:
    """Ask Endurain what it already holds, HTTP first then postgres.

    Returns None only when *neither* backend could answer, which the caller
    must read as "unknown" rather than "nothing stored" -- an empty list is a
    real answer and means this user genuinely has no activities.

    The HTTP path is tried first even though it cannot currently succeed, so
    that the supported route starts working on its own if Endurain ever widens
    the API-key scope allow-list.
    """
    starts = client.recent_start_times(user_id)
    if starts is not None:
        _logger.info(
            "duplicate detection: %d activity start time(s) via the API", len(starts)
        )
        return starts

    if os.environ.get(_NO_DB_ENV) == "1":
        _logger.warning(
            "duplicate detection against Endurain is unavailable and the "
            "database fallback is disabled; falling back to the local ledger only"
        )
        return None

    starts = EndurainDatabase().recent_start_times(user_id)
    if starts is None:
        _logger.warning(
            "duplicate detection against Endurain is unavailable; falling "
            "back to the local ledger only"
        )
        return None
    _logger.info(
        "duplicate detection: %d activity start time(s) via the database", len(starts)
    )
    return starts

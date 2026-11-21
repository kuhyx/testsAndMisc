"""The lease file, and the acquire operation that waits in its fair queue.

One JSON file per phone holds every live lease on it, the queue of callers
waiting for one, and the start of each whole-phone hold. A lease has a *scope*:

* ``pkg:<package>`` -- one app (install, launch, driving it). Two sessions can
  hold different packages at once. ``pkg:__screen__`` is the phone's real
  screen, and the default, so callers written before scopes keep their meaning.
* ``whole-phone`` -- anything that changes the phone for everyone (forced
  Doze, screen sleep, reboot, a focus-mode deploy). It conflicts with every
  foreign lease, is capped at :data:`WHOLE_PHONE_MAX_TTL`, and carries cleanup
  commands that run exactly once, on release or expiry.

The queue rules live in :mod:`._queue`; this module only loads and saves the
file under ``flock`` and runs cleanup commands outside the lock.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import fcntl
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.phone_lease import _cleanup, _queue
from python_pkg.phone_lease import owner as owner_mod
from python_pkg.phone_lease._model import (
    DEFAULT_TTL,
    DEFAULT_WAIT,
    QUEUED_EXIT,
    SCREEN,
    TICKET_TTL,
    WHOLE_PHONE,
    WHOLE_PHONE_MAX_TTL,
    Clock,
    Lease,
    PhoneBusyError,
    PhoneQueuedError,
    Ticket,
    scope_of,
)
from python_pkg.phone_lease._queue import Book
from python_pkg.phone_lease.owner import owner_id

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "DEFAULT_TTL",
    "DEFAULT_WAIT",
    "QUEUED_EXIT",
    "SCREEN",
    "TICKET_TTL",
    "WHOLE_PHONE",
    "WHOLE_PHONE_MAX_TTL",
    "Clock",
    "Lease",
    "PhoneBusyError",
    "PhoneQueuedError",
    "Terms",
    "Ticket",
    "acquire",
    "scope_of",
]

# Where lease files live; overridable so tests never touch the real one.
LEASE_DIR = Path(
    os.environ.get("PHONE_LEASE_DIR", str(Path.home() / ".cache" / "phone-lease"))
)


def lease_paths(serial: str) -> tuple[Path, Path]:
    """The lock file and the lease file for ``serial``."""
    LEASE_DIR.mkdir(parents=True, exist_ok=True)
    safe = serial.replace("/", "_")
    return LEASE_DIR / f"{safe}.lock", LEASE_DIR / f"{safe}.json"


def _parse(raw: object) -> Lease | None:
    if not isinstance(raw, dict):
        return None
    try:
        lease = Lease(**raw)
    except TypeError:
        return None
    return Lease(**{**asdict(lease), "cleanup": tuple(lease.cleanup)})


def _ticket(raw: object) -> Ticket | None:
    if not isinstance(raw, dict):
        return None
    try:
        return Ticket(**raw)
    except TypeError:
        return None


def read_book(path: Path) -> Book:
    """Everything in the file; damaged parts read as empty.

    Pre-scope files hold one bare lease object, pre-queue files only leases.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return Book()
    if not isinstance(raw, dict):
        return Book()
    leases = [x for x in map(_parse, raw.get("leases", [raw])) if x is not None]
    queue = raw.get("queue", [])
    tickets = [x for x in map(_ticket, queue if isinstance(queue, list) else []) if x]
    after = max((x.number for x in tickets), default=0) + 1
    number = raw.get("next")
    since = raw.get("since")
    return Book(
        leases=leases,
        tickets=tickets,
        next_number=max(number, after) if isinstance(number, int) else after,
        since=dict(since) if isinstance(since, dict) else {},
    )


def read_leases(path: Path) -> list[Lease]:
    """Every lease in the file, expired or not."""
    return read_book(path).leases


def write_book(path: Path, book: Book) -> None:
    """Replace the file's contents with ``book``."""
    body = {
        "leases": [asdict(x) for x in book.leases],
        "queue": [asdict(x) for x in book.tickets],
        "next": book.next_number,
        "since": book.since,
    }
    path.write_text(json.dumps(body), encoding="utf-8")


def locked_update[T](serial: str, change: Callable[[Book, float], T], now: float) -> T:
    """Apply ``change`` to the tidied book under the lock and return its result.

    Expired leases and those of dead owners are dropped first (:func:`._queue.tidy`);
    their cleanup commands run after the lock is released, so a slow ``adb``
    never blocks another session.
    """
    lock_path, path = lease_paths(serial)
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        book = read_book(path)
        # Looked up on each call so tests (and conftest) can patch owner_alive.
        gone = _queue.tidy(book, now, owner_mod.owner_alive)
        result = change(book, now)
        write_book(path, book)
    for lease in gone:
        _cleanup.run(lease.cleanup)
    return result


@dataclass(frozen=True)
class Terms:
    """How long to hold, how long to wait, and what to undo afterwards."""

    ttl: float = DEFAULT_TTL
    wait: float = DEFAULT_WAIT
    cleanup: tuple[str, ...] = ()


def _queued_message(grant: _queue.Grant, wait: float) -> str:
    return (
        f"{grant.blocker} -- waited {wait:.0f}s; you are #{grant.position} in line "
        f"(ticket {grant.number}). To keep your place, rerun the same command "
        f"within {TICKET_TTL:.0f}s. Or drive the app on your own virtual display "
        "(~/.claude/scripts/phone_vd.sh, needs only a package lease), or the "
        "headless emulator (~/.claude/scripts/phone_emu.sh); see the phone-deploy "
        "skill."
    )


def acquire(
    serial: str,
    note: str = "",
    *,
    scope: str = f"pkg:{SCREEN}",
    terms: Terms | None = None,
    owner: str | None = None,
    clock: Clock | None = None,
) -> Lease:
    """Take or refresh a lease on ``serial`` for one ``scope`` (see :func:`scope_of`).

    Waits in line up to ``terms.wait`` seconds, polling once a second, then
    raises :class:`PhoneQueuedError` with the caller's ticket kept.
    """
    me = owner_id() if owner is None else owner
    terms = terms or Terms()
    clock = clock or Clock()
    want = Lease(serial, me, 0.0, note, scope, terms.cleanup)
    deadline = clock.now() + terms.wait
    while True:
        grant = locked_update(
            serial,
            lambda book, at: _queue.take(book, want, terms.ttl, at),
            clock.now(),
        )
        if grant.lease is not None:
            if grant.new_cleanup:
                _cleanup.spawn_reaper(serial, me, scope)
            return grant.lease
        if clock.now() >= deadline:
            raise PhoneQueuedError(
                _queued_message(grant, terms.wait),
                position=grant.position,
                number=grant.number,
            )
        clock.sleep(1.0)

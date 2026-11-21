"""The fair queue, as pure functions over one lease file's contents.

No files and no clock here: :func:`python_pkg.phone_lease.lease.locked_update`
loads a :class:`Book` under the flock, calls :func:`tidy` and then one of
:func:`take` / :func:`leave`, and writes it back. The rules:

* a caller is granted a scope when no foreign lease conflicts with it and no
  foreign ticket that conflicts with it has a lower number than its own;
  everyone else gets a ticket (kept :data:`TICKET_TTL` after each attempt)
  and its position in line. Different packages never conflict, so they are
  granted side by side;
* a holder's refresh never pushes its expiry out while a conflicting foreign
  ticket waits (the *drain* rule), so busy holders cannot starve the line;
* a whole-phone hold ends :data:`WHOLE_PHONE_MAX_TTL` after its first grant;
* leases and tickets of dead owners are dropped at once (:func:`tidy`).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from python_pkg.phone_lease._model import (
    TICKET_TTL,
    WHOLE_PHONE,
    WHOLE_PHONE_MAX_TTL,
    Lease,
    Ticket,
    conflicts,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class Book:
    """Everything one lease file holds."""

    leases: list[Lease] = field(default_factory=list)
    tickets: list[Ticket] = field(default_factory=list)
    next_number: int = 1
    # "<owner> <scope>" -> first grant of a whole-phone hold, for its cap.
    since: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Grant:
    """What one attempt got: a lease, or a place in line and who is ahead."""

    lease: Lease | None
    position: int = 0
    number: int = 0
    blocker: str = ""
    new_cleanup: bool = False


def _key(owner: str, scope: str) -> str:
    return f"{owner} {scope}"


def tidy(book: Book, now: float, alive: Callable[[str], bool]) -> list[Lease]:
    """Drop expired or orphaned leases and tickets; return the dropped leases.

    The caller runs the dropped leases' cleanup commands (outside the lock).
    """
    keep: list[Lease] = []
    gone: list[Lease] = []
    for lease in book.leases:
        (keep if not lease.is_expired(now) and alive(lease.owner) else gone).append(
            lease
        )
    book.leases = keep
    book.tickets = [
        x for x in book.tickets if now < x.seen + TICKET_TTL and alive(x.owner)
    ]
    held = {_key(x.owner, x.scope) for x in keep}
    book.since = {k: v for k, v in book.since.items() if k in held}
    return gone


def take(book: Book, want: Lease, ttl: float, now: float) -> Grant:
    """Grant or refresh ``want`` if the line allows it, else queue it."""
    key = (want.owner, want.scope)
    held = next((x for x in book.leases if (x.owner, x.scope) == key), None)
    mine = next((x for x in book.tickets if (x.owner, x.scope) == key), None)
    rivals = [
        x
        for x in book.tickets
        if x.owner != want.owner and conflicts(x.scope, want.scope)
    ]
    if held is None:
        blocker = next(
            (x for x in book.leases if x.conflicts_with(want.owner, want.scope)),
            None,
        )
        ahead = [x for x in rivals if mine is None or x.number < mine.number]
        if blocker is not None or ahead:
            first = blocker.describe() if blocker is not None else ahead[0].describe()
            return _queue(book, want, mine, len(ahead) + 1, first, now)
    return _grant(book, want, held, ttl, now, drain=bool(rivals))


def _grant(
    book: Book, want: Lease, held: Lease | None, ttl: float, now: float, *, drain: bool
) -> Grant:
    key = _key(want.owner, want.scope)
    expires = now + ttl
    if want.scope == WHOLE_PHONE:
        start = book.since.get(key, now) if held is not None else now
        book.since[key] = start
        expires = min(expires, start + WHOLE_PHONE_MAX_TTL)
    old: tuple[str, ...] = ()
    if held is not None:
        old = held.cleanup
        if drain:
            expires = held.expires
    cleanup = old + tuple(c for c in dict.fromkeys(want.cleanup) if c not in old)
    granted = replace(want, expires=expires, cleanup=cleanup)
    book.leases = [x for x in book.leases if x is not held] + [granted]
    book.tickets = [
        x for x in book.tickets if (x.owner, x.scope) != (want.owner, want.scope)
    ]
    return Grant(granted, new_cleanup=bool(cleanup) and not old)


def _queue(
    book: Book, want: Lease, mine: Ticket | None, position: int, first: str, now: float
) -> Grant:
    if mine is None:
        mine = Ticket(want.owner, want.scope, book.next_number, now, want.note)
        book.next_number += 1
        book.tickets.append(mine)
    else:
        fresh = replace(mine, seen=now, note=want.note)
        book.tickets = [fresh if x is mine else x for x in book.tickets]
    return Grant(None, position=position, number=mine.number, blocker=first)


def leave(book: Book, owner: str, scope: str) -> tuple[list[Lease], bool]:
    """Drop ``owner``'s lease and ticket on ``scope``.

    Returns the dropped leases (their cleanup is the caller's) and whether
    anything at all was dropped.
    """
    mine = (owner, scope)
    dropped = [x for x in book.leases if (x.owner, x.scope) == mine]
    tickets = [x for x in book.tickets if (x.owner, x.scope) != mine]
    found = bool(dropped) or len(tickets) < len(book.tickets)
    book.leases = [x for x in book.leases if (x.owner, x.scope) != mine]
    book.tickets = tickets
    book.since.pop(_key(owner, scope), None)
    return dropped, found

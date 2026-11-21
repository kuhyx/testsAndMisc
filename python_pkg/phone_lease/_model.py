"""The lease file's records, its constants, and the errors ``acquire`` raises.

Split out of ``lease.py`` so the pure queue core (:mod:`._queue`) and the
file layer (:mod:`.lease`) share one definition without importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class Clock:
    """The two things ``acquire`` needs from ``time``; tests hand in fakes."""

    now: Callable[[], float] = time.time
    sleep: Callable[[float], None] = time.sleep


# Seconds a lease outlives its last refresh; a quiet session frees the phone.
DEFAULT_TTL = 180.0
# Seconds ``acquire`` waits in the queue before answering "queued, retry".
# Every Claude tool call is capped at 60 s, so a wait must end well before.
DEFAULT_WAIT = 50.0
# A whole-phone hold stops everyone else: 30 s from its first grant, however
# often the holder refreshes it.
WHOLE_PHONE_MAX_TTL = 30.0
# Seconds a queue ticket survives its owner's last attempt, so a caller that
# got "queued" and reruns the same command keeps its place in line.
TICKET_TTL = 90.0
# Exit code for "queued, retry": EX_TEMPFAIL from sysexits.h.
QUEUED_EXIT = 75
SCREEN = "__screen__"
WHOLE_PHONE = "whole-phone"


class PhoneBusyError(RuntimeError):
    """Raised when a fresh, conflicting lease belongs to another owner."""


class PhoneQueuedError(PhoneBusyError):
    """The wait ran out with the caller still in line; its ticket is kept."""

    def __init__(self, message: str, *, position: int, number: int) -> None:
        """Keep the place in line next to the message."""
        super().__init__(message)
        self.position = position
        self.number = number


def conflicts(scope: str, other: str) -> bool:
    """Whether two owners may not hold ``scope`` and ``other`` at once."""
    return WHOLE_PHONE in (scope, other) or scope == other


@dataclass(frozen=True)
class Lease:
    """One entry of the lease file."""

    serial: str
    owner: str
    expires: float
    note: str
    scope: str = f"pkg:{SCREEN}"
    cleanup: tuple[str, ...] = field(default_factory=tuple)

    def is_expired(self, now: float) -> bool:
        """True once ``now`` has passed the expiry."""
        return now >= self.expires

    def conflicts_with(self, owner: str, scope: str) -> bool:
        """Whether this lease stops ``owner`` from taking ``scope``."""
        return self.owner != owner and conflicts(self.scope, scope)

    def describe(self) -> str:
        """One line for an error or a status readout."""
        until = time.strftime("%H:%M:%S", time.localtime(self.expires))
        what = "" if self.scope == f"pkg:{SCREEN}" else f" [{self.scope}]"
        return (
            f"phone {self.serial}{what} held by {self.owner} ({self.note}) "
            f"until {until}"
        )


@dataclass(frozen=True)
class Ticket:
    """One caller waiting in line for a scope; ``number`` orders the line."""

    owner: str
    scope: str
    number: int
    seen: float
    note: str = ""

    def describe(self) -> str:
        """One line for an error or a status readout."""
        return f"queued #{self.number} {self.owner} [{self.scope}] ({self.note})"


def scope_of(package: str | None = None, *, whole_phone: bool = False) -> str:
    """The scope string for a package, the whole phone, or the real screen."""
    if whole_phone:
        return WHOLE_PHONE
    return f"pkg:{package or SCREEN}"

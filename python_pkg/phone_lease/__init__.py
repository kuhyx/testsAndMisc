"""One phone, many Claude sessions: leases that keep them from colliding.

Two sessions driving the same phone interleave their taps -- on 2026-09-20 a
tap meant for the workout sandbox landed in another session's manga reader,
twice. This package hands out *scoped* leases:

* the leases are one JSON file per serial under ``~/.cache/phone-lease/``,
  guarded by ``flock`` so read-modify-write is atomic across processes;
* a lease covers one app (``--package``), the real screen (the default), or
  the whole phone (``--whole-phone``: Doze, sleep, reboot -- capped at five
  minutes, with cleanup commands a detached reaper runs if nobody releases);
* the owner is the nearest ancestor ``claude`` process (one per session);
* the serial is always resolved (:mod:`.serial`), never a placeholder, so
  every caller agrees on which phone a lease is for;
* a lease expires ``ttl`` seconds after its last refresh;
* callers that find their scope taken wait in a fair FIFO queue: each gets a
  ticket it keeps for :data:`TICKET_TTL` seconds after its last try, and
  leases and tickets of sessions that died are dropped at once.

Sessions that drive apps on their own virtual display
(``~/.claude/scripts/phone_vd.sh``) need only a package lease, so several of
them can work on one phone at the same time.
"""

from python_pkg.phone_lease import _cleanup
from python_pkg.phone_lease.lease import (
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
    Terms,
    Ticket,
    acquire,
    scope_of,
)
from python_pkg.phone_lease.ops import (
    holds,
    queue_of,
    reap,
    release,
    status,
    status_all,
)
from python_pkg.phone_lease.owner import owner_alive, owner_id
from python_pkg.phone_lease.serial import NoPhoneError, resolve_serial

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
    "NoPhoneError",
    "PhoneBusyError",
    "PhoneQueuedError",
    "Terms",
    "Ticket",
    "_cleanup",
    "acquire",
    "holds",
    "owner_alive",
    "owner_id",
    "queue_of",
    "reap",
    "release",
    "resolve_serial",
    "scope_of",
    "status",
    "status_all",
]

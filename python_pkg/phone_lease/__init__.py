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
* a lease expires ``ttl`` seconds after its last refresh.

Sessions that drive apps on their own virtual display
(``~/.claude/scripts/phone_vd.sh``) need only a package lease, so several of
them can work on one phone at the same time.
"""

from python_pkg.phone_lease.lease import (
    DEFAULT_TTL,
    DEFAULT_WAIT,
    SCREEN,
    WHOLE_PHONE,
    WHOLE_PHONE_MAX_TTL,
    Clock,
    Lease,
    PhoneBusyError,
    Terms,
    acquire,
    scope_of,
)
from python_pkg.phone_lease.ops import holds, reap, release, status, status_all
from python_pkg.phone_lease.owner import owner_id
from python_pkg.phone_lease.serial import NoPhoneError, resolve_serial

__all__ = [
    "DEFAULT_TTL",
    "DEFAULT_WAIT",
    "SCREEN",
    "WHOLE_PHONE",
    "WHOLE_PHONE_MAX_TTL",
    "Clock",
    "Lease",
    "NoPhoneError",
    "PhoneBusyError",
    "Terms",
    "acquire",
    "holds",
    "owner_id",
    "reap",
    "release",
    "resolve_serial",
    "scope_of",
    "status",
    "status_all",
]

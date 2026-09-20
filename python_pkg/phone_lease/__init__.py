"""One phone, many Claude sessions: a lease that keeps them from colliding.

Two sessions driving the same phone interleave their taps -- on 2026-09-20 a
tap meant for the workout sandbox landed in another session's manga reader,
twice. This package hands the phone to one owner at a time:

* the lease is a JSON file per serial under ``~/.cache/phone-lease/``, guarded
  by ``flock`` so read-modify-write is atomic across processes;
* the owner is the nearest ancestor ``claude`` process (one per session), so
  every call from the same session refreshes the same lease and calls from
  another session wait, then fail naming the holder;
* it expires ``ttl`` seconds after the last refresh, so a session that just
  stops driving frees the phone without anyone remembering to release.

``android_ui`` takes the lease on every command and ``phone_deploy.sh`` on
every deploy, which is every path that touches the phone from a session.
"""

from python_pkg.phone_lease.lease import (
    DEFAULT_TTL,
    DEFAULT_WAIT,
    Clock,
    Lease,
    PhoneBusyError,
    acquire,
    owner_id,
    release,
    status,
)

__all__ = [
    "DEFAULT_TTL",
    "DEFAULT_WAIT",
    "Clock",
    "Lease",
    "PhoneBusyError",
    "acquire",
    "owner_id",
    "release",
    "status",
]

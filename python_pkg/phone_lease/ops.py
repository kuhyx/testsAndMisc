"""Release, status, the ``holds`` check the adb hook asks, and the reaper."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from python_pkg.phone_lease import _cleanup
from python_pkg.phone_lease.lease import (
    SCREEN,
    WHOLE_PHONE,
    Clock,
    Lease,
    lease_paths,
    locked_update,
    read_leases,
)
from python_pkg.phone_lease.owner import owner_id

if TYPE_CHECKING:
    from collections.abc import Callable

# Longest the reaper sleeps between looks at the lease file.
REAP_POLL = 5.0


def release(
    serial: str, *, scope: str = f"pkg:{SCREEN}", owner: str | None = None
) -> bool:
    """Drop ``owner``'s lease on ``scope``, running its cleanup. True if dropped."""
    me = owner_id() if owner is None else owner
    dropped: list[Lease] = []

    def drop(live: list[Lease], _now: float) -> list[Lease]:
        dropped.extend(x for x in live if (x.owner, x.scope) == (me, scope))
        return [x for x in live if x not in dropped]

    locked_update(serial, drop, time.time())
    for lease in dropped:
        _cleanup.run(lease.cleanup)
    return bool(dropped)


def status_all(serial: str, now: float | None = None) -> list[Lease]:
    """Every live lease on ``serial`` (read-only: no cleanup runs here)."""
    at = time.time() if now is None else now
    return [x for x in read_leases(lease_paths(serial)[1]) if not x.is_expired(at)]


def status(
    serial: str, now: float | None = None, *, scope: str = f"pkg:{SCREEN}"
) -> Lease | None:
    """The live lease on ``scope``, or None when free."""
    return next((x for x in status_all(serial, now) if x.scope == scope), None)


def holds(
    serial: str, owner: str, scope: str = f"pkg:{SCREEN}", now: float | None = None
) -> bool:
    """Whether ``owner`` may act on ``scope`` right now.

    True when it holds that scope or the whole phone. This is the question
    the raw-adb hook asks before letting an ``input``/``am`` through.
    """
    return any(
        x.owner == owner and x.scope in {scope, WHOLE_PHONE}
        for x in status_all(serial, now)
    )


def reap(
    serial: str,
    owner: str,
    scope: str,
    *,
    clock: Clock | None = None,
    alive: Callable[[], bool] = lambda: True,
) -> bool:
    """Wait until ``owner``'s lease on ``scope`` ends; run its cleanup if it expired.

    Refreshes push the expiry out, so this re-reads the file after every
    sleep. Returns True when it ran the cleanup, False when the holder
    released first (``release`` already ran it) or ``alive`` says stop.
    """
    clock = clock or Clock()
    while alive():
        lease = next(
            (
                x
                for x in read_leases(lease_paths(serial)[1])
                if (x.owner, x.scope) == (owner, scope)
            ),
            None,
        )
        if lease is None:
            return False
        if lease.is_expired(clock.now()):
            # locked_update drops expired leases and runs their cleanup itself.
            locked_update(serial, lambda live, _now: live, clock.now())
            return True
        # Wake at least every few seconds so a released lease frees the reaper.
        clock.sleep(min(REAP_POLL, max(0.5, lease.expires - clock.now())))
    return False

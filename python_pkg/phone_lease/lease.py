"""The lease file, its owner identity, and the acquire/release operations.

One JSON file per phone holds every live lease on it. A lease has a *scope*:

* ``pkg:<package>`` -- one app (install, launch, driving it). Two sessions can
  hold different packages at once. ``pkg:__screen__`` is the phone's real
  screen, and the default, so callers written before scopes keep their meaning.
* ``whole-phone`` -- anything that changes the phone for everyone (forced
  Doze, screen sleep, reboot, a focus-mode deploy). It conflicts with every
  foreign lease, is capped at :data:`WHOLE_PHONE_MAX_TTL`, and carries cleanup
  commands that run exactly once, on release or expiry.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import fcntl
import json
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING

from python_pkg.phone_lease import _cleanup
from python_pkg.phone_lease.owner import owner_id

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class Clock:
    """The two things ``acquire`` needs from ``time``; tests hand in fakes."""

    now: Callable[[], float] = time.time
    sleep: Callable[[float], None] = time.sleep


# Seconds a lease outlives its last refresh; a quiet session frees the phone.
DEFAULT_TTL = 180.0
# Seconds ``acquire`` waits on a foreign lease before giving up.
DEFAULT_WAIT = 60.0
# A whole-phone lease stops everyone else, so it can never be held for long.
WHOLE_PHONE_MAX_TTL = 300.0
SCREEN = "__screen__"
WHOLE_PHONE = "whole-phone"
# Where lease files live; overridable so tests never touch the real one.
LEASE_DIR = Path(
    os.environ.get("PHONE_LEASE_DIR", str(Path.home() / ".cache" / "phone-lease"))
)


class PhoneBusyError(RuntimeError):
    """Raised when a fresh, conflicting lease belongs to another owner."""


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
        if self.owner == owner:
            return False
        return WHOLE_PHONE in (self.scope, scope) or self.scope == scope

    def describe(self) -> str:
        """One line for an error or a status readout."""
        until = time.strftime("%H:%M:%S", time.localtime(self.expires))
        what = "" if self.scope == f"pkg:{SCREEN}" else f" [{self.scope}]"
        return (
            f"phone {self.serial}{what} held by {self.owner} ({self.note}) "
            f"until {until}"
        )


def scope_of(package: str | None = None, *, whole_phone: bool = False) -> str:
    """The scope string for a package, the whole phone, or the real screen."""
    if whole_phone:
        return WHOLE_PHONE
    return f"pkg:{package or SCREEN}"


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


def read_leases(path: Path) -> list[Lease]:
    """Every lease in the file. Pre-scope files hold one bare object."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return []
    items = raw.get("leases", [raw]) if isinstance(raw, dict) else []
    return [lease for lease in map(_parse, items) if lease is not None]


def write_leases(path: Path, leases: list[Lease]) -> None:
    """Replace the lease file's contents with ``leases``."""
    path.write_text(
        json.dumps({"leases": [asdict(lease) for lease in leases]}), encoding="utf-8"
    )


def locked_update(
    serial: str, change: Callable[[list[Lease], float], list[Lease]], now: float
) -> list[Lease]:
    """Apply ``change`` to the live leases under the lock.

    Expired leases are dropped on the way in; their cleanup commands run after
    the lock is released, so a slow ``adb`` never blocks another session.
    """
    lock_path, lease_path = lease_paths(serial)
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        leases = read_leases(lease_path)
        expired = [lease for lease in leases if lease.is_expired(now)]
        live = change([lease for lease in leases if not lease.is_expired(now)], now)
        write_leases(lease_path, live)
    for lease in expired:
        _cleanup.run(lease.cleanup)
    return live


def _attempt(
    serial: str, want: Lease, ttl: float, now: float
) -> tuple[Lease | None, Lease | None, bool]:
    """One locked try at ``want``: (granted lease, blocker, newly taken)."""
    out: list[Lease | None] = [None, None]
    fresh = [True]

    def take(live: list[Lease], at: float) -> list[Lease]:
        blocker = next(
            (x for x in live if x.conflicts_with(want.owner, want.scope)), None
        )
        if blocker is not None:
            out[1] = blocker
            return live
        prior = next(
            (x for x in live if (x.owner, x.scope) == (want.owner, want.scope)), None
        )
        fresh[0] = prior is None
        granted = Lease(**{**asdict(want), "expires": at + ttl})
        out[0] = granted
        return [x for x in live if x is not prior] + [granted]

    locked_update(serial, take, now)
    return out[0], out[1], fresh[0]


@dataclass(frozen=True)
class Terms:
    """How long to hold, how long to wait, and what to undo afterwards."""

    ttl: float = DEFAULT_TTL
    wait: float = DEFAULT_WAIT
    cleanup: tuple[str, ...] = ()


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

    Waits up to ``terms.wait`` seconds for conflicting foreign leases to
    expire, polling once a second, then raises :class:`PhoneBusyError`.
    """
    me = owner_id() if owner is None else owner
    terms = terms or Terms()
    ttl = terms.ttl
    if scope == WHOLE_PHONE:
        ttl = min(ttl, WHOLE_PHONE_MAX_TTL)
    cleanup = terms.cleanup
    wait = terms.wait
    clock = clock or Clock()
    deadline = clock.now() + wait
    while True:
        mine, blocker, is_new = _attempt(
            serial, Lease(serial, me, 0.0, note, scope, cleanup), ttl, clock.now()
        )
        if mine is not None:
            if is_new and cleanup:
                _cleanup.spawn_reaper(serial, me, scope)
            return mine
        if clock.now() >= deadline:
            msg = (
                f"{blocker.describe() if blocker else serial} -- waited {wait:.0f}s. "
                "Do not retry "
                "in a loop: drive the app on your own virtual display instead "
                "(~/.claude/scripts/phone_vd.sh, needs only a package lease), or the "
                "headless emulator (~/.claude/scripts/phone_emu.sh); see the "
                "phone-deploy skill."
            )
            raise PhoneBusyError(msg)
        clock.sleep(1.0)

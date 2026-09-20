"""The lease file, its owner identity, and the acquire/release operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import fcntl
import json
import os
from pathlib import Path
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

# Seconds ``acquire`` waits on a foreign lease before giving up.
DEFAULT_WAIT = 60.0

# Where lease files live; overridable so tests never touch the real one.
LEASE_DIR = Path(
    os.environ.get("PHONE_LEASE_DIR", str(Path.home() / ".cache" / "phone-lease"))
)

# Set this to name the owner explicitly (CI, a script without a claude parent).
OWNER_ENV = "PHONE_LEASE_OWNER"


class PhoneBusyError(RuntimeError):
    """Raised when a fresh lease belongs to another owner."""


@dataclass(frozen=True)
class Lease:
    """What the lease file says."""

    serial: str
    owner: str
    expires: float
    note: str

    def is_expired(self, now: float) -> bool:
        """True once ``now`` has passed the expiry."""
        return now >= self.expires

    def describe(self) -> str:
        """One line for an error or a status readout."""
        until = time.strftime("%H:%M:%S", time.localtime(self.expires))
        return f"phone {self.serial} held by {self.owner} ({self.note}) until {until}"


def owner_id(pid: int | None = None, environ: dict[str, str] | None = None) -> str:
    """Identify the calling session.

    ``PHONE_LEASE_OWNER`` wins. Otherwise walk up from ``pid`` (this process
    by default) to the nearest ancestor whose ``comm`` is ``claude`` -- one
    per session -- and fall back to this process's own pid when there is none.
    """
    env = os.environ if environ is None else environ
    explicit = env.get(OWNER_ENV)
    if explicit:
        return explicit
    current = os.getpid() if pid is None else pid
    origin = current
    while current > 1:
        try:
            comm = Path(f"/proc/{current}/comm").read_text(encoding="utf-8").strip()
            stat = Path(f"/proc/{current}/stat").read_text(encoding="utf-8")
        except OSError:
            break
        if comm == "claude":
            return f"claude:{current}"
        # Field 4 of /proc/<pid>/stat is the parent pid; the comm field before
        # it may contain spaces, so split after its closing paren.
        current = int(stat.rsplit(")", 1)[1].split()[1])
    return f"pid:{origin}"


def _paths(serial: str) -> tuple[Path, Path]:
    LEASE_DIR.mkdir(parents=True, exist_ok=True)
    safe = serial.replace("/", "_")
    return LEASE_DIR / f"{safe}.lock", LEASE_DIR / f"{safe}.json"


def _read(path: Path) -> Lease | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    try:
        return Lease(**raw)
    except TypeError:
        return None


def _locked_update(
    serial: str,
    owner: str,
    note: str,
    ttl: float,
    now: float,
) -> Lease:
    """One atomic attempt: take or refresh the lease, or return the holder's."""
    lock_path, lease_path = _paths(serial)
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = _read(lease_path)
        if (
            current is not None
            and current.owner != owner
            and not current.is_expired(now)
        ):
            return current
        fresh = Lease(serial=serial, owner=owner, expires=now + ttl, note=note)
        lease_path.write_text(json.dumps(asdict(fresh)), encoding="utf-8")
        return fresh


def acquire(
    serial: str,
    note: str = "",
    *,
    owner: str | None = None,
    ttl: float = DEFAULT_TTL,
    wait: float = DEFAULT_WAIT,
    clock: Clock | None = None,
) -> Lease:
    """Take or refresh the lease on ``serial``.

    Waits up to ``wait`` seconds for a foreign lease to expire, polling once a
    second, then raises :class:`PhoneBusyError` naming the holder.
    """
    me = owner_id() if owner is None else owner
    clock = clock or Clock()
    deadline = clock.now() + wait
    while True:
        lease = _locked_update(serial, me, note, ttl, clock.now())
        if lease.owner == me:
            return lease
        if clock.now() >= deadline:
            msg = (
                f"{lease.describe()} -- waited {wait:.0f}s. Do not retry in a loop: "
                "drive a sandbox-flavor app on the phone's virtual display instead "
                "(~/.claude/scripts/phone_vd.sh, needs no lease), or the headless "
                "emulator (~/.claude/scripts/phone_emu.sh); see the phone-deploy skill."
            )
            raise PhoneBusyError(msg)
        clock.sleep(1.0)


def release(serial: str, *, owner: str | None = None) -> bool:
    """Drop the lease if ``owner`` holds it. Returns whether anything was dropped."""
    me = owner_id() if owner is None else owner
    lock_path, lease_path = _paths(serial)
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = _read(lease_path)
        if current is None or current.owner != me:
            return False
        lease_path.unlink()
        return True


def status(serial: str, now: float | None = None) -> Lease | None:
    """The live lease on ``serial``, or None when free or expired."""
    _, lease_path = _paths(serial)
    current = _read(lease_path)
    if current is None or current.is_expired(time.time() if now is None else now):
        return None
    return current

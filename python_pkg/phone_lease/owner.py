"""Which Claude session is calling: the identity every lease is held under."""

from __future__ import annotations

import os
from pathlib import Path

# Set this to name the owner explicitly (CI, a script without a claude parent).
OWNER_ENV = "PHONE_LEASE_OWNER"


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


def owner_alive(owner: str, *, proc_root: Path = Path("/proc")) -> bool:
    """Whether ``owner``'s session still runs, so its leases and tickets stay.

    ``claude:<pid>`` lives while that pid is a ``claude`` process (a reused pid
    running anything else counts as dead); ``<tool>:<pid>`` lives while the pid
    exists. ``pid:<pid>`` is the CLI's own short-lived process, and explicit
    names (``PHONE_LEASE_OWNER``) carry no pid, so both always count as alive.
    """
    kind, _, pid = owner.partition(":")
    if not pid.isdigit() or kind == "pid":
        return True
    comm = proc_root / pid / "comm"
    if kind != "claude":
        return comm.parent.exists()
    try:
        return comm.read_text(encoding="utf-8").strip() == "claude"
    except OSError:
        return False

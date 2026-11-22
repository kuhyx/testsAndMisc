"""Which session owns which virtual display, read from ``phone_vd.sh`` state.

``phone_vd.sh`` keeps one directory per session under
``$PHONE_VD_STATE_DIR/<serial>/<owner>/`` holding ``display`` (the logical id
``input -d`` takes), ``sf`` (the SurfaceFlinger id ``screencap -d`` takes) and
``package``. The owner directory name is the phone_lease owner id with
anything outside ``[A-Za-z0-9_.-]`` replaced by ``_``, exactly as the script
writes it.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]")


def state_root() -> Path:
    """The directory ``phone_vd.sh`` keeps its per-phone state in.

    Mirrors ``phone_vd_state_root`` in ``~/.claude/scripts/lib/phone_vd_dir.sh``:
    ``$PHONE_VD_STATE_DIR`` (the test seam) if non-empty, else
    ``${XDG_RUNTIME_DIR:-/run/user/<uid>}/phone_vd`` when that runtime dir
    exists, else ``/tmp/phone_vd``. ``TMPDIR`` is never read, so a session
    with a private ``TMPDIR`` sees the same directory as the shell side.
    """
    override = os.environ.get("PHONE_VD_STATE_DIR")
    if override:
        return Path(override)
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}")
    if runtime.is_dir():
        return runtime / "phone_vd"
    return Path("/", "tmp", "phone_vd")


def owner_dir_name(owner: str) -> str:
    """``owner`` as ``phone_vd.sh`` names its state directory."""
    return _UNSAFE.sub("_", owner)


@dataclass(frozen=True)
class SessionDisplay:
    """One running virtual display and whose it is."""

    owner_dir: str
    display: int
    sf: str
    package: str


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def displays(serial: str) -> list[SessionDisplay]:
    """Every session's virtual display on ``serial``."""
    root = state_root() / serial
    found: list[SessionDisplay] = []
    if not root.is_dir():
        return found
    for entry in sorted(root.iterdir()):
        display = _read(entry / "display")
        if not display.isdigit():
            continue
        found.append(
            SessionDisplay(
                owner_dir=entry.name,
                display=int(display),
                sf=_read(entry / "sf"),
                package=_read(entry / "package"),
            )
        )
    return found


def own_display(serial: str, owner: str) -> SessionDisplay | None:
    """``owner``'s virtual display on ``serial``, if it has one running."""
    mine = owner_dir_name(owner)
    return next((d for d in displays(serial) if d.owner_dir == mine), None)


def display_owner(serial: str, display: int) -> SessionDisplay | None:
    """The session whose virtual display has logical id ``display``."""
    return next((d for d in displays(serial) if d.display == display), None)

"""Inputs a style may read, injectable for tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_CACHE = Path.home() / ".cache" / "wallpaper_rotator"


@dataclass(frozen=True)
class RenderContext:
    """Where the data-driven styles read from, and what time it is.

    Attributes:
        now: Current local time (timezone-aware).
        data_home: ``~/.local/share``, holding the guards' ledgers.
        earth_dir: Holds ``day.jpg`` and ``night.jpg`` (see install.sh).
        shutdown_conf: screen-locker's schedule file.
    """

    now: datetime
    data_home: Path
    earth_dir: Path
    shutdown_conf: Path

    @classmethod
    def live(cls) -> RenderContext:
        """Build the context for the running desktop."""
        return cls(
            now=datetime.now().astimezone(),
            data_home=Path.home() / ".local" / "share",
            earth_dir=DEFAULT_CACHE / "earth",
            shutdown_conf=Path("/etc/shutdown-schedule.conf"),
        )

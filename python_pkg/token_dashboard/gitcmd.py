"""One way to run git for the dashboard: absolute binary, bounded, never raises."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

GIT = shutil.which("git") or "/usr/bin/git"
TIMEOUT_S = 30


def run(repo: str | Path, *args: str, stdin: str | None = None) -> str | None:
    """``git -C repo args``: stdout, or ``None`` on any failure."""
    try:
        done = subprocess.run(
            [GIT, "-C", str(repo), *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT_S,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    return done.stdout if done.returncode == 0 else None

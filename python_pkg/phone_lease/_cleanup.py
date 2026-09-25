"""Run a whole-phone lease's cleanup commands, even if nobody releases it.

A forced Doze left behind by a crashed session breaks every other session's
network and alarms until someone notices, so cleanup cannot depend on the
holder remembering: a detached reaper watches each lease that has cleanup
commands and runs them the moment it expires.
"""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

# One cleanup command may not hang the reaper or a caller's release.
CLEANUP_TIMEOUT = 30.0
# The repo root, so the detached reaper can import python_pkg from anywhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def run(commands: Iterable[str]) -> list[int]:
    """Run each command (no shell), returning exit codes; never raises.

    A failing or missing command is reported as a non-zero code rather than
    raised, because the remaining cleanup steps must still run.
    """
    codes: list[int] = []
    for command in commands:
        try:
            done = subprocess.run(
                shlex.split(command),
                check=False,
                timeout=CLEANUP_TIMEOUT,
                capture_output=True,
            )
        except OSError, ValueError, subprocess.TimeoutExpired:
            codes.append(127)
            continue
        codes.append(done.returncode)
    return codes


def spawn_reaper(serial: str, owner: str, scope: str) -> None:
    """Start a detached ``phone_lease reap`` for one freshly taken lease."""
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT)}
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "python_pkg.phone_lease",
            "reap",
            serial,
            "--owner",
            owner,
            "--scope",
            scope,
        ],
        env=env,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

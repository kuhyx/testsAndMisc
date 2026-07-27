"""Storage locations, resolved lazily.

Every path is a *function*. A module-level ``Path.home() / ...`` constant is
evaluated at import time, which makes it impossible for a test to redirect --
``brother_printer.consumables`` learned that the hard way. Resolving on each
call keeps the whole package redirectable from one fixture.

Nothing in this module deletes anything; ``trash_dir`` is a destination, not a
bin that gets emptied.
"""

from __future__ import annotations

import os
from pathlib import Path

from python_pkg.wsg_grabber.constants import BOARD

_APP_DIRNAME = "wsg_grabber"


def data_dir() -> Path:
    """Return the root directory holding the index and every downloaded file.

    Honours ``XDG_DATA_HOME`` when set, else ``~/.local/share``.

    Returns:
        Path: ``<data home>/wsg_grabber`` (not guaranteed to exist).
    """
    override = os.environ.get("XDG_DATA_HOME")
    base = Path(override) if override else Path.home() / ".local" / "share"
    return base / _APP_DIRNAME


def db_path() -> Path:
    """Return the sqlite index file.

    Returns:
        Path: ``<data dir>/index.db``.
    """
    return data_dir() / "index.db"


def incoming_dir() -> Path:
    """Return the directory holding downloaded, not-yet-reviewed videos.

    Returns:
        Path: ``<data dir>/incoming``.
    """
    return data_dir() / "incoming"


def keep_dir() -> Path:
    """Return the directory videos are moved to when kept.

    Returns:
        Path: ``<data dir>/keep``.
    """
    return data_dir() / "keep"


def trash_dir() -> Path:
    """Return the directory videos are moved to when passed.

    Nothing ever removes files from here; clearing it is the user's call.

    Returns:
        Path: ``<data dir>/trash``.
    """
    return data_dir() / "trash"


def ipc_socket_path() -> Path:
    """Return the unix socket used to drive the embedded mpv process.

    Returns:
        Path: ``<data dir>/mpv-<board>.sock``.
    """
    return data_dir() / f"mpv-{BOARD}.sock"


def ensure_dirs() -> None:
    """Create the data, incoming, keep and trash directories if absent."""
    for directory in (data_dir(), incoming_dir(), keep_dir(), trash_dir()):
        directory.mkdir(parents=True, exist_ok=True)

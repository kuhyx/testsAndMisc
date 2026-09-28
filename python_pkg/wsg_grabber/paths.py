"""Storage locations, resolved lazily.

Every path is a *function*. A module-level ``Path.home() / ...`` constant is
evaluated at import time, which makes it impossible for a test to redirect --
``brother_printer.consumables`` learned that the hard way. Resolving on each
call keeps the whole package redirectable from one fixture.

Kept videos leave the data dir entirely: they go to the dufs cloud folder
(``~/data/cloud/Media/<year>/wsg``) so they show up in the gallery and on the
phone, or to ``~/Downloads`` on a machine without the cloud folder. Both are
resolved per call, so the answer follows the filesystem rather than the process
start time.

Nothing in this module deletes anything; ``trash_dir`` is a destination.
:mod:`python_pkg.wsg_grabber._prune` is what keeps it bounded.
"""

from __future__ import annotations

from datetime import UTC, datetime
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


def cloud_root() -> Path:
    """Return the folder dufs serves as the personal cloud.

    Returns:
        Path: ``~/data/cloud`` (may not exist on this machine).
    """
    return Path.home() / "data" / "cloud"


def downloads_dir() -> Path:
    """Return the fallback destination for kept videos.

    Returns:
        Path: ``~/Downloads``.
    """
    return Path.home() / "Downloads"


def cloud_keep_dir(year: int) -> Path:
    """Return the cloud folder kept videos go to for *year*.

    Args:
        year: Calendar year of the keep verdict.

    Returns:
        Path: ``<cloud>/Media/<year>/wsg``.
    """
    return cloud_root() / "Media" / str(year) / "wsg"


def keep_dir() -> Path:
    """Return the directory videos are moved to when kept.

    The cloud folder wins whenever it exists; otherwise ``~/Downloads``, which
    is at least somewhere a person looks.

    Returns:
        Path: ``<cloud>/Media/<this year>/wsg`` or ``~/Downloads``.
    """
    if cloud_root().is_dir():
        return cloud_keep_dir(datetime.now(tz=UTC).astimezone().year)
    return downloads_dir()


def legacy_keep_dir() -> Path:
    """Return where kept videos used to go before they moved to the cloud.

    Only :mod:`python_pkg.wsg_grabber._migrate_keep` should care.

    Returns:
        Path: ``<data dir>/keep``.
    """
    return data_dir() / "keep"


def kept_candidates() -> list[Path]:
    """Return every directory a kept video may be sitting in, most likely first.

    Undo has to find a file that ``keep_dir()`` would not name today: a keep
    from last year, one made while the cloud folder was absent, one the
    media-cloud-sync timer has since swept out of ``~/Downloads`` into
    ``Media/<year>/<month>``, or one still in the pre-cloud ``keep/``.

    Returns:
        list[Path]: Candidate directories; entries need not exist.
    """
    media = cloud_root() / "Media"
    return [
        keep_dir(),
        *sorted(media.glob("*/wsg")),
        legacy_keep_dir(),
        downloads_dir(),
        *sorted(p for p in media.glob("*/*") if p.is_dir() and p.name != "wsg"),
    ]


def trash_dir() -> Path:
    """Return the directory videos are moved to when passed.

    Bounded to the newest ``TRASH_RETAIN`` passes by
    :mod:`python_pkg.wsg_grabber._prune`; older ones are deleted for good.

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

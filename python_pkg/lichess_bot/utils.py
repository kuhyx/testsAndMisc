"""Utility functions for the Lichess bot."""

import logging
import os
from pathlib import Path
import time

_logger = logging.getLogger(__name__)


def _version_file_path() -> str:
    """Return the path to the persistent bot version file.

    Stored alongside this module as a simple text file containing an integer.
    """
    override = os.getenv("LICHESS_BOT_VERSION_FILE")
    if override:
        return override
    return str(Path(__file__).parent / ".bot_version")


def get_and_increment_version() -> int:
    """Read the current bot version, increment it, persist, and return the new version.

    If the version file doesn't exist or is invalid, starts from 0, then sets to 1.
    """
    path = _version_file_path()
    current = 0
    try:
        with Path(path).open(encoding="utf-8") as f:
            raw = f.read().strip()
            if raw:
                current = int(raw)
    except (OSError, ValueError):
        # Missing or unreadable file -> treat as version 0
        current = 0

    new_version = current + 1
    try:
        tmp_path = Path(path + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            f.write(str(new_version))
        tmp_path.replace(path)
    except OSError:
        # As a fallback, try a direct write; failure is non-fatal to bot operation
        try:
            with Path(path).open("w", encoding="utf-8") as f:
                f.write(str(new_version))
        except OSError:
            _logger.debug("Could not persist bot version to %s", path)

    return new_version


def backoff_sleep(current_backoff: int, base: float = 0.5, cap: float = 8.0) -> int:
    """Sleep with exponential backoff. Returns the next backoff step.

    - current_backoff: number of consecutive failures
    - base: base delay in seconds
    - cap: maximum delay in seconds
    """
    delay = min(cap, base * (2**current_backoff))
    _logger.info("Backing off for %.1fs", delay)
    time.sleep(delay)
    return min(current_backoff + 1, 10)

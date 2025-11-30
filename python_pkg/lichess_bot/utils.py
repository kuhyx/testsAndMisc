"""Utility functions for the Lichess bot."""

import logging
import os
import time


def _version_file_path() -> str:
    """Return the path to the persistent bot version file.

    Stored alongside this module as a simple text file containing an integer.
    """
    override = os.getenv("LICHESS_BOT_VERSION_FILE")
    if override:
        return override
    return os.path.join(os.path.dirname(__file__), ".bot_version")


def get_and_increment_version() -> int:
    """Read the current bot version, increment it, persist, and return the new version.

    If the version file doesn't exist or is invalid, starts from 0, then sets to 1.
    """
    path = _version_file_path()
    current = 0
    try:
        with open(path) as f:
            raw = f.read().strip()
            if raw:
                current = int(raw)
    except (OSError, ValueError):
        # Missing or unreadable file -> treat as version 0
        current = 0

    new_version = current + 1
    try:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            f.write(str(new_version))
        os.replace(tmp_path, path)
    except OSError:
        # As a fallback, try a direct write; failure is non-fatal to bot operation
        try:
            with open(path, "w") as f:
                f.write(str(new_version))
        except OSError:
            logging.debug("Could not persist bot version to %s", path)

    return new_version


def backoff_sleep(current_backoff: int, base: float = 0.5, cap: float = 8.0) -> int:
    """Sleep with exponential backoff. Returns the next backoff step.

    - current_backoff: number of consecutive failures
    - base: base delay in seconds
    - cap: maximum delay in seconds
    """
    delay = min(cap, base * (2**current_backoff))
    logging.info(f"Backing off for {delay:.1f}s")
    time.sleep(delay)
    return min(current_backoff + 1, 10)

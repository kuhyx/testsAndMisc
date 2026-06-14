"""Shared logging configuration for python_pkg entry points."""

from __future__ import annotations

import logging


def configure_logging() -> None:
    """Configure root logging with the standard daemon format and level.

    Centralises the ``basicConfig`` call shared by the package ``main`` entry
    points so every daemon logs with an identical timestamped format.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

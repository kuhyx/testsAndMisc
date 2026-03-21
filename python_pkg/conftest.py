"""Top-level conftest: clean up logging handlers to avoid bad-FD on exit."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True, scope="session")
def _cleanup_logging_handlers_at_end() -> Iterator[None]:
    """Remove all root logging handlers after the test session.

    Prevents ``OSError: [Errno 9] Bad file descriptor`` when pre-commit
    closes file descriptors before the logging atexit handler runs
    (observed on Python 3.14).
    """
    yield
    root = logging.getLogger()
    for handler in root.handlers[:]:
        with contextlib.suppress(OSError):
            handler.close()
        root.removeHandler(handler)
    logging.shutdown()

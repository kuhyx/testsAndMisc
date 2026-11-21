"""Every lease test runs with live owners unless it says otherwise.

Tests name owners ``claude:1``, ``claude:2`` ...; on a real machine pid 1 is
systemd, so the dead-owner reaper would drop those leases mid-test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def owners_alive() -> Iterator[None]:
    """Treat every owner as alive; reaping tests patch their own answer."""
    with patch("python_pkg.phone_lease.owner.owner_alive", return_value=True):
        yield

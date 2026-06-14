"""Tests for the shared logging configuration helper."""

from __future__ import annotations

import logging
from unittest.mock import patch

from python_pkg.shared.logging_setup import configure_logging


def test_configure_logging_uses_standard_format_and_level() -> None:
    """``configure_logging`` delegates to ``basicConfig`` with INFO + format."""
    with patch(
        "python_pkg.shared.logging_setup.logging.basicConfig",
    ) as mock_basic_config:
        configure_logging()
    mock_basic_config.assert_called_once_with(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

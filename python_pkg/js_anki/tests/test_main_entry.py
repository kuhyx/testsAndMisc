"""Tests for js_anki.__main__ module."""

from __future__ import annotations

import runpy
import sys
from unittest.mock import MagicMock, patch

import pytest


def test_main_called_when_run_as_module() -> None:
    mock_main = MagicMock(return_value=0)
    sys.modules.pop("python_pkg.js_anki.__main__", None)
    with (
        patch("python_pkg.js_anki.cli.main", mock_main),
        pytest.raises(SystemExit) as excinfo,
    ):
        runpy.run_module("python_pkg.js_anki", run_name="__main__")
    assert excinfo.value.code == 0
    mock_main.assert_called_once()


def test_main_not_called_on_plain_import() -> None:
    mock_main = MagicMock()
    sys.modules.pop("python_pkg.js_anki.__main__", None)
    with patch("python_pkg.js_anki.cli.main", mock_main):
        __import__("python_pkg.js_anki.__main__")
    mock_main.assert_not_called()

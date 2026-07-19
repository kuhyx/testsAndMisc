"""Tests for app_icons.__main__ module."""

from __future__ import annotations

import importlib
import runpy
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestMain:
    def test_main_called_when_run_as_module(self) -> None:
        """python3 -m python_pkg.app_icons runs main() and exits with its status."""
        mock_main = MagicMock(return_value=0)
        # runpy warns if __main__ is already imported, and the suite runs tests
        # in a random order, so another test may have imported it first.
        sys.modules.pop("python_pkg.app_icons.__main__", None)
        with (
            patch("python_pkg.app_icons.cli.main", mock_main),
            pytest.raises(SystemExit) as excinfo,
        ):
            runpy.run_module("python_pkg.app_icons", run_name="__main__")
        assert excinfo.value.code == 0
        mock_main.assert_called_once()

    def test_main_not_called_on_plain_import(self) -> None:
        """Importing __main__ must not generate icons as a side effect."""
        mock_main = MagicMock()
        with patch("python_pkg.app_icons.cli.main", mock_main):
            sys.modules.pop("python_pkg.app_icons.__main__", None)
            importlib.import_module("python_pkg.app_icons.__main__")
        mock_main.assert_not_called()

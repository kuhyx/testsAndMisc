"""Tests for brother_printer.__main__ module."""

from __future__ import annotations

import importlib
import runpy
import sys
from unittest.mock import MagicMock, patch


class TestMain:
    def test_main_called_when_run_as_module(self) -> None:
        """python3 -m python_pkg.brother_printer runs main()."""
        mock_main = MagicMock()
        with patch(
            "python_pkg.brother_printer.check_brother_printer.main",
            mock_main,
        ):
            runpy.run_module("python_pkg.brother_printer", run_name="__main__")
        mock_main.assert_called_once()

    def test_main_not_called_on_plain_import(self) -> None:
        """Importing __main__ must not fire off a status report as a side effect."""
        mock_main = MagicMock()
        with patch(
            "python_pkg.brother_printer.check_brother_printer.main",
            mock_main,
        ):
            sys.modules.pop("python_pkg.brother_printer.__main__", None)
            importlib.import_module("python_pkg.brother_printer.__main__")
        mock_main.assert_not_called()

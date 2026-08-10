"""Tests for the archwiki_rag module entry point."""

from __future__ import annotations

import runpy
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestModuleEntry:
    @patch("python_pkg.archwiki_rag.cli.main", return_value=0)
    def test_runs_cli_main(self, mock_main: MagicMock) -> None:
        with (
            patch.object(sys, "argv", ["python_pkg.archwiki_rag", "sync"]),
            pytest.raises(SystemExit) as excinfo,
        ):
            runpy.run_module("python_pkg.archwiki_rag", run_name="__main__")

        assert excinfo.value.code == 0
        mock_main.assert_called_once()

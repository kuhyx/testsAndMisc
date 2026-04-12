"""Tests for python_pkg.fm24_searcher.__main__."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from python_pkg.fm24_searcher.__main__ import _main


class TestMain:
    """__main__ dispatch tests."""

    def test_dump_mode(self) -> None:
        with (
            patch("sys.argv", ["fm24", "--dump", "--db", "/nonexistent"]),
            patch(
                "python_pkg.fm24_searcher.cli.run_dump",
                return_value=0,
            ) as mock_dump,
        ):
            with pytest.raises(SystemExit) as exc_info:
                _main()
            assert exc_info.value.code == 0
            mock_dump.assert_called_once()

    def test_gui_mode(self) -> None:
        with (
            patch("sys.argv", ["fm24"]),
            patch(
                "python_pkg.fm24_searcher.gui.main",
            ) as mock_gui,
        ):
            _main()
            mock_gui.assert_called_once()

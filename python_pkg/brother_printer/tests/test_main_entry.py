"""Tests for brother_printer.__main__ module."""

from __future__ import annotations

import importlib
import types
from unittest.mock import MagicMock, patch


class TestMain:
    def test_main_called(self) -> None:
        """Test that __main__ calls main()."""
        mock_main = MagicMock()
        # Create a fake brother_printer.check_brother_printer module
        fake_module = types.ModuleType("brother_printer.check_brother_printer")
        vars(fake_module)["main"] = mock_main
        with patch.dict(
            "sys.modules",
            {
                "brother_printer": types.ModuleType("brother_printer"),
                "brother_printer.check_brother_printer": fake_module,
            },
        ):
            # Remove cached __main__ module so it gets re-imported
            import sys

            sys.modules.pop("python_pkg.brother_printer.__main__", None)
            importlib.import_module("python_pkg.brother_printer.__main__")
            mock_main.assert_called_once()

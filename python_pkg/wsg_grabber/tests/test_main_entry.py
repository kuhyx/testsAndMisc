"""Tests for the ``python -m python_pkg.wsg_grabber`` entry point."""

from __future__ import annotations

import runpy
import sys
from unittest.mock import patch

import pytest

_MODULE = "python_pkg.wsg_grabber.__main__"


def test_running_as_a_module_exits_with_the_cli_status() -> None:
    # pytest-randomly shuffles test order, so a previous import must not linger
    sys.modules.pop(_MODULE, None)
    with (
        patch("python_pkg.wsg_grabber.cli.main", return_value=3) as entry,
        pytest.raises(SystemExit) as exit_info,
    ):
        runpy.run_module(_MODULE, run_name="__main__")
    assert exit_info.value.code == 3
    entry.assert_called_once_with()


def test_importing_the_module_has_no_side_effect() -> None:
    sys.modules.pop(_MODULE, None)
    with patch("python_pkg.wsg_grabber.cli.main") as entry:
        runpy.run_module(_MODULE, run_name="not_main")
    entry.assert_not_called()

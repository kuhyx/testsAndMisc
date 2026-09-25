"""``python -m python_pkg.phone_guard`` runs the hook."""

from __future__ import annotations

import runpy
from unittest.mock import patch

import pytest


def test_module_entry_exits_with_the_hook_code() -> None:
    with (
        patch("python_pkg.phone_guard.hook.main", return_value=2),
        pytest.raises(SystemExit) as done,
    ):
        runpy.run_module("python_pkg.phone_guard", run_name="__main__")
    assert done.value.code == 2

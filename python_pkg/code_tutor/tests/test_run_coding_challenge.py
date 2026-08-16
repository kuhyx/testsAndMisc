"""Tests for the run_coding_challenge entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._challenge_flows import (
    run_coding_challenge,
)
from python_pkg.code_tutor.tests.conftest import _item

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# run_coding_challenge
# ---------------------------------------------------------------------------


def test_run_coding_challenge_non_python() -> None:
    mock_console = MagicMock()
    mock_backend = MagicMock()
    result = run_coding_challenge(
        _item(file="main.go"),
        "/codebase",
        "explanation",
        mock_backend,
        mock_console,
    )
    assert result == "skipped"


def test_run_coding_challenge_with_existing_tests(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): fn()\n", encoding="utf-8")
    mock_console = MagicMock()
    mock_backend = MagicMock()

    with patch(
        "python_pkg.code_tutor._challenge_flows._existing_tests_flow",
        return_value="passed",
    ):
        result = run_coding_challenge(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            mock_backend,
            mock_console,
        )
    assert result == "passed"


def test_run_coding_challenge_no_tests(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    mock_console = MagicMock()
    mock_backend = MagicMock()

    with patch(
        "python_pkg.code_tutor._challenge_flows._write_tests_first_flow",
        return_value="skipped",
    ):
        result = run_coding_challenge(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            mock_backend,
            mock_console,
        )
    assert result == "skipped"

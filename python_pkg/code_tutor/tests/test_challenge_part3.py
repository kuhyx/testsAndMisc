"""Tests for python_pkg.code_tutor._challenge -- part 3.

Covers the user-implementation runner and the two challenge flows plus the
public entry point: ``_run_user_impl``, ``_write_tests_first_flow``,
``_existing_tests_flow`` and ``run_coding_challenge``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._challenge import _run_user_impl
from python_pkg.code_tutor.tests.conftest import _item, _make_live_mock

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# _run_user_impl
# ---------------------------------------------------------------------------


def test_run_user_impl_skip(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    live_mock = _make_live_mock()

    with (
        patch("python_pkg.code_tutor._verdict.Live", return_value=live_mock),
        patch("python_pkg.code_tutor._challenge.Syntax"),
    ):
        result = _run_user_impl(
            _item(file="mod.py"),
            str(tmp_path),
            "def test_fn(): pass",
            "# import",
            mock_console,
            lambda _: "skip",
        )
    assert result == "skipped"


def test_run_user_impl_syntax_error(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    inputs = iter(["def (broken):", ""])

    with patch("python_pkg.code_tutor._challenge.Syntax"):
        result = _run_user_impl(
            _item(file="mod.py"),
            str(tmp_path),
            "def test_fn(): pass",
            "# import",
            mock_console,
            lambda _: next(inputs, "END") if _ == "" else "END",
        )

    # Provide the END and the broken implementation
    inputs2 = iter(["def (broken):", "END"])

    with patch("python_pkg.code_tutor._challenge.Syntax"):
        result = _run_user_impl(
            _item(file="mod.py"),
            str(tmp_path),
            "def test_fn(): pass",
            "# import",
            mock_console,
            lambda _: next(inputs2),
        )
    assert result == "failed"


def test_run_user_impl_passed(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    inputs = iter(["def fn():", "    return 42", "END"])

    with (
        patch("python_pkg.code_tutor._challenge.Syntax"),
        patch("python_pkg.code_tutor._challenge._pytest_clean", return_value=True),
    ):
        result = _run_user_impl(
            _item(file="mod.py"),
            str(tmp_path),
            "def test_fn(): pass",
            "# import",
            mock_console,
            lambda _: next(inputs),
        )
    assert result == "passed"
    # File restored
    assert (tmp_path / "mod.py").read_text(encoding="utf-8") == source


def test_run_user_impl_failed(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    inputs = iter(["def fn():", "    return 0", "END"])

    with (
        patch("python_pkg.code_tutor._challenge.Syntax"),
        patch("python_pkg.code_tutor._challenge._pytest_clean", return_value=False),
    ):
        result = _run_user_impl(
            _item(file="mod.py"),
            str(tmp_path),
            "def test_fn(): pass",
            "# import",
            mock_console,
            lambda _: next(inputs),
        )
    assert result == "failed"
    assert (tmp_path / "mod.py").read_text(encoding="utf-8") == source

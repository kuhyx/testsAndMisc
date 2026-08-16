"""Tests for the two code_tutor challenge flows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._challenge_flows import (
    _existing_tests_flow,
    _write_tests_first_flow,
)
from python_pkg.code_tutor.tests.conftest import _item

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# _write_tests_first_flow
# ---------------------------------------------------------------------------


def test_write_tests_first_flow_user_declines(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    mock_backend = MagicMock()
    mock_console = MagicMock()

    result = _write_tests_first_flow(
        _item(file="mod.py"),
        str(tmp_path),
        "explanation",
        mock_backend,
        mock_console,
        lambda _: "n",
    )
    assert result == "skipped"


def test_write_tests_first_flow_tests_none(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    mock_backend = MagicMock()
    mock_console = MagicMock()

    with (
        patch(
            "python_pkg.code_tutor._challenge_flows._collect_and_rate_tests",
            return_value=None,
        ),
        patch("python_pkg.code_tutor._challenge_flows.Syntax"),
    ):
        result = _write_tests_first_flow(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            mock_backend,
            mock_console,
            lambda _: "y",
        )
    assert result == "skipped"


def test_write_tests_first_flow_tests_fail_real(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    mock_backend = MagicMock()
    mock_console = MagicMock()

    with (
        patch(
            "python_pkg.code_tutor._challenge_flows._collect_and_rate_tests",
            return_value="test code",
        ),
        patch(
            "python_pkg.code_tutor._challenge_flows._validate_tests_against_real",
            return_value=False,
        ),
        patch("python_pkg.code_tutor._challenge_flows.Syntax"),
    ):
        result = _write_tests_first_flow(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            mock_backend,
            mock_console,
            lambda _: "y",
        )
    assert result == "skipped"


def test_write_tests_first_flow_success(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    mock_backend = MagicMock()
    mock_console = MagicMock()

    with (
        patch(
            "python_pkg.code_tutor._challenge_flows._collect_and_rate_tests",
            return_value="test code",
        ),
        patch(
            "python_pkg.code_tutor._challenge_flows._validate_tests_against_real",
            return_value=True,
        ),
        patch(
            "python_pkg.code_tutor._challenge_flows._run_user_impl",
            return_value="passed",
        ),
        patch("python_pkg.code_tutor._challenge_flows.Syntax"),
    ):
        result = _write_tests_first_flow(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            mock_backend,
            mock_console,
            lambda _: "y",
        )
    assert result == "passed"


# ---------------------------------------------------------------------------
# _existing_tests_flow
# ---------------------------------------------------------------------------


def test_existing_tests_flow_user_declines(tmp_path: Path) -> None:
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): fn()\n", encoding="utf-8")
    mock_console = MagicMock()
    result = _existing_tests_flow(
        _item(),
        str(tmp_path),
        "explanation",
        [(test_file, ["test_fn"])],
        mock_console,
        lambda _: "n",
    )
    assert result == "skipped"


def test_existing_tests_flow_user_skips_impl(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): fn()\n", encoding="utf-8")
    mock_console = MagicMock()

    with patch("python_pkg.code_tutor._challenge_support.Syntax"):
        result = _existing_tests_flow(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            [(test_file, ["test_fn"])],
            mock_console,
            lambda _: (
                "y"
                if "challenge" in str(_) or _ == "Take the challenge? [y/N] "
                else "skip"
            ),
        )
    assert result == "skipped"


def test_existing_tests_flow_passes(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): fn()\n", encoding="utf-8")
    mock_console = MagicMock()

    inputs = iter(["y", "def fn():", "    return 1", "END"])

    with (
        patch("python_pkg.code_tutor._challenge_support.Syntax"),
        patch(
            "python_pkg.code_tutor._challenge_flows._patch_and_test", return_value=True
        ),
    ):
        result = _existing_tests_flow(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            [(test_file, ["test_fn"])],
            mock_console,
            lambda _: next(inputs),
        )
    assert result == "passed"


def test_existing_tests_flow_fails(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): fn()\n", encoding="utf-8")
    mock_console = MagicMock()

    inputs = iter(["y", "def fn():", "    return 0", "END"])

    with (
        patch("python_pkg.code_tutor._challenge_support.Syntax"),
        patch(
            "python_pkg.code_tutor._challenge_flows._patch_and_test", return_value=False
        ),
    ):
        result = _existing_tests_flow(
            _item(file="mod.py"),
            str(tmp_path),
            "explanation",
            [(test_file, ["test_fn"])],
            mock_console,
            lambda _: next(inputs),
        )
    assert result == "failed"

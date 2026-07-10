"""Tests for python_pkg.code_tutor._challenge -- part 3.

Covers the user-implementation runner and the two challenge flows plus the
public entry point: ``_run_user_impl``, ``_write_tests_first_flow``,
``_existing_tests_flow`` and ``run_coding_challenge``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._challenge import (
    _existing_tests_flow,
    _run_user_impl,
    _write_tests_first_flow,
    run_coding_challenge,
)
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
        patch("python_pkg.code_tutor._challenge_support.Live", return_value=live_mock),
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
            "python_pkg.code_tutor._challenge._collect_and_rate_tests",
            return_value=None,
        ),
        patch("python_pkg.code_tutor._challenge.Syntax"),
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
            "python_pkg.code_tutor._challenge._collect_and_rate_tests",
            return_value="test code",
        ),
        patch(
            "python_pkg.code_tutor._challenge._validate_tests_against_real",
            return_value=False,
        ),
        patch("python_pkg.code_tutor._challenge.Syntax"),
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
            "python_pkg.code_tutor._challenge._collect_and_rate_tests",
            return_value="test code",
        ),
        patch(
            "python_pkg.code_tutor._challenge._validate_tests_against_real",
            return_value=True,
        ),
        patch(
            "python_pkg.code_tutor._challenge._run_user_impl",
            return_value="passed",
        ),
        patch("python_pkg.code_tutor._challenge.Syntax"),
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
        patch("python_pkg.code_tutor._challenge._patch_and_test", return_value=True),
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
        patch("python_pkg.code_tutor._challenge._patch_and_test", return_value=False),
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
        "python_pkg.code_tutor._challenge._existing_tests_flow", return_value="passed"
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
        "python_pkg.code_tutor._challenge._write_tests_first_flow",
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

"""Tests for python_pkg.code_tutor._pytest_runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._challenge_support import (
    _scan_test_file,
    _show_test_panels,
)
from python_pkg.code_tutor._pytest_runner import _patch_and_test, _pytest_clean
from python_pkg.code_tutor.tests.conftest import _item

# ---------------------------------------------------------------------------
# _pytest_clean
# ---------------------------------------------------------------------------


def test_pytest_clean_pass() -> None:
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "1 passed"
    mock_result.stderr = ""
    mock_console = MagicMock()
    with patch(
        "python_pkg.code_tutor._pytest_runner.subprocess.run",
        return_value=mock_result,
    ):
        assert (
            _pytest_clean(["test_mod.py::test_fn"], Path("/proj"), mock_console) is True
        )


def test_pytest_clean_fail() -> None:
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "FAILED"
    mock_console = MagicMock()
    with patch(
        "python_pkg.code_tutor._pytest_runner.subprocess.run",
        return_value=mock_result,
    ):
        assert (
            _pytest_clean(["test_mod.py::test_fn"], Path("/proj"), mock_console)
            is False
        )


def test_pytest_clean_no_output() -> None:
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_console = MagicMock()
    with patch(
        "python_pkg.code_tutor._pytest_runner.subprocess.run",
        return_value=mock_result,
    ):
        _pytest_clean([], Path("/proj"), mock_console)
    mock_console.print.assert_not_called()


# ---------------------------------------------------------------------------
# _patch_and_test
# ---------------------------------------------------------------------------


def test_patch_and_test_syntax_error(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    result = _patch_and_test(
        _item(file="mod.py", start=1, end=2),
        str(tmp_path),
        "def fn(\n    broken syntax",
        [],
        mock_console,
    )
    assert result is False
    # Original file should be restored
    assert (tmp_path / "mod.py").read_text(encoding="utf-8") == source


def test_patch_and_test_passes(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): pass\n", encoding="utf-8")
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._pytest_runner._pytest_clean", return_value=True):
        result = _patch_and_test(
            _item(file="mod.py", start=1, end=2),
            str(tmp_path),
            "def fn():\n    return 99",
            [(test_file, ["test_fn"])],
            mock_console,
        )
    assert result is True
    # File restored
    assert (tmp_path / "mod.py").read_text(encoding="utf-8") == source


def test_patch_and_test_fails(tmp_path: Path) -> None:
    source = "def fn():\n    return 1\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): pass\n", encoding="utf-8")
    mock_console = MagicMock()
    with patch(
        "python_pkg.code_tutor._pytest_runner._pytest_clean", return_value=False
    ):
        result = _patch_and_test(
            _item(file="mod.py", start=1, end=2),
            str(tmp_path),
            "def fn():\n    return 0",
            [(test_file, ["test_fn"])],
            mock_console,
        )
    assert result is False
    assert (tmp_path / "mod.py").read_text(encoding="utf-8") == source


def test_scan_test_file_non_func_non_class_toplevel() -> None:
    """Skip a top-level node that is neither a function nor a class def.

    A module-level ``import`` fails both ``isinstance`` checks, exercising
    the branch that falls through the ``elif ClassDef`` back to the loop.
    """
    source = "import os\ndef test_fn_uses_fn():\n    fn()\n"
    result = _scan_test_file(source, "fn")
    assert result == ["test_fn_uses_fn"]


def test_show_test_panels_non_func_non_class_toplevel(tmp_path: Path) -> None:
    """Skip a top-level node that is neither a function nor a class def.

    A module-level ``import`` yields an empty ``nodes`` list, so the
    ``elif ClassDef`` branch is not taken before the inner render loop.
    """
    source = "import os\ndef test_fn():\n    fn(1)\n"
    test_file = tmp_path / "test_mod.py"
    test_file.write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._challenge_support.Syntax"):
        _show_test_panels([(test_file, ["test_fn"])], mock_console)
    assert mock_console.print.called


def test_show_test_panels_class_non_func_member(tmp_path: Path) -> None:
    """Skip a class-body member that is not a function definition.

    The class-level ``attr = 1`` assignment fails the member ``isinstance``
    check, exercising the branch that loops back to the next body member.
    """
    source = "class TestFoo:\n    attr = 1\n    def test_fn(self):\n        fn()\n"
    test_file = tmp_path / "test_mod.py"
    test_file.write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._challenge_support.Syntax"):
        _show_test_panels([(test_file, ["TestFoo::test_fn"])], mock_console)
    assert mock_console.print.called

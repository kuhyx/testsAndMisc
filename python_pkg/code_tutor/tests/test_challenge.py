"""Tests for python_pkg.code_tutor._challenge_support -- part 1.

Covers the test-discovery and pytest-execution helpers:
``_scan_test_file``, ``_find_tests``, ``_show_test_panels``,
``_collect_lines``, ``_project_root``, ``_pytest_clean`` and
``_patch_and_test``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._challenge_support import (
    _collect_lines,
    _find_tests,
    _patch_and_test,
    _project_root,
    _pytest_clean,
    _scan_test_file,
    _show_test_panels,
)
from python_pkg.code_tutor.tests.conftest import _item

# ---------------------------------------------------------------------------
# _scan_test_file
# ---------------------------------------------------------------------------


def test_scan_test_file_module_function_match() -> None:
    source = "def test_fn_does_thing():\n    fn(1)\n"
    result = _scan_test_file(source, "fn")
    assert "test_fn_does_thing" in result


def test_scan_test_file_class_method_match() -> None:
    source = "class TestFoo:\n    def test_fn_works(self):\n        fn()\n"
    result = _scan_test_file(source, "fn")
    assert any("test_fn_works" in r for r in result)


def test_scan_test_file_no_match() -> None:
    source = "def test_other():\n    other()\n"
    result = _scan_test_file(source, "fn")
    assert result == []


def test_scan_test_file_syntax_error() -> None:
    result = _scan_test_file("def (broken):", "fn")
    assert result == []


def test_scan_test_file_non_test_function_skipped() -> None:
    source = "def helper_fn():\n    fn()\n"
    result = _scan_test_file(source, "fn")
    assert result == []


# ---------------------------------------------------------------------------
# _find_tests
# ---------------------------------------------------------------------------


def test_find_tests_found(tmp_path: Path) -> None:
    (tmp_path / "test_mod.py").write_text(
        "def test_fn_works():\n    fn()\n", encoding="utf-8"
    )
    result = _find_tests(_item(), tmp_path)
    assert len(result) == 1
    assert result[0][1] == ["test_fn_works"]


def test_find_tests_no_name_in_source(tmp_path: Path) -> None:
    (tmp_path / "test_other.py").write_text(
        "def test_other_works():\n    other()\n", encoding="utf-8"
    )
    result = _find_tests(_item(), tmp_path)
    assert result == []


def test_find_tests_oserror(tmp_path: Path) -> None:
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): fn()\n", encoding="utf-8")
    with patch("pathlib.Path.read_text", side_effect=OSError("perm")):
        result = _find_tests(_item(), tmp_path)
    assert result == []


def test_find_tests_no_matching_node_ids(tmp_path: Path) -> None:
    # File mentions 'fn' in source but not in test function bodies
    (tmp_path / "test_mod.py").write_text(
        "# fn is mentioned here\ndef test_other():\n    pass\n", encoding="utf-8"
    )
    result = _find_tests(_item(), tmp_path)
    assert result == []


# ---------------------------------------------------------------------------
# _show_test_panels
# ---------------------------------------------------------------------------


def test_show_test_panels_normal(tmp_path: Path) -> None:
    source = "def test_fn():\n    fn(1)\n    assert True\n"
    test_file = tmp_path / "test_mod.py"
    test_file.write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._challenge_support.Syntax"):
        _show_test_panels([(test_file, ["test_fn"])], mock_console)
    assert mock_console.print.called


def test_show_test_panels_class_method(tmp_path: Path) -> None:
    source = "class TestFoo:\n    def test_fn(self):\n        fn()\n"
    test_file = tmp_path / "test_mod.py"
    test_file.write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._challenge_support.Syntax"):
        _show_test_panels([(test_file, ["TestFoo::test_fn"])], mock_console)
    assert mock_console.print.called


def test_show_test_panels_oserror(tmp_path: Path) -> None:
    test_file = tmp_path / "test_mod.py"
    test_file.write_text("def test_fn(): pass\n", encoding="utf-8")
    mock_console = MagicMock()
    with patch("pathlib.Path.read_text", side_effect=OSError("perm")):
        _show_test_panels([(test_file, ["test_fn"])], mock_console)
    mock_console.print.assert_not_called()


def test_show_test_panels_node_not_in_func_names(tmp_path: Path) -> None:
    source = "def test_fn():\n    fn()\n"
    test_file = tmp_path / "test_mod.py"
    test_file.write_text(source, encoding="utf-8")
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._challenge_support.Syntax"):
        # Pass a node_id that doesn't match any function name
        _show_test_panels([(test_file, ["test_other"])], mock_console)
    mock_console.print.assert_not_called()


# ---------------------------------------------------------------------------
# _collect_lines
# ---------------------------------------------------------------------------


def test_collect_lines_end() -> None:
    responses = iter(["line one", "line two", "END"])
    mock_console = MagicMock()
    result = _collect_lines("prompt", mock_console, lambda _: next(responses))
    assert result == "line one\nline two"


def test_collect_lines_skip() -> None:
    mock_console = MagicMock()
    result = _collect_lines("prompt", mock_console, lambda _: "skip")
    assert result is None


# ---------------------------------------------------------------------------
# _project_root
# ---------------------------------------------------------------------------


def test_project_root_finds_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    sub = tmp_path / "src" / "pkg"
    sub.mkdir(parents=True)
    result = _project_root(sub)
    assert result == tmp_path


def test_project_root_finds_setup_py(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text("# setup", encoding="utf-8")
    result = _project_root(tmp_path)
    assert result == tmp_path


def test_project_root_not_found(tmp_path: Path) -> None:
    # Create a dir deep inside tmp_path with no pyproject/setup
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    # Walk up to root (tmp_path's parent and above) without finding the files
    # We need a completely isolated path — create one without any pyproject.toml
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        isolated = Path(td) / "pkg"
        isolated.mkdir()
        result = _project_root(isolated)
        # When not found, returns start.resolve()
        assert result == isolated.resolve()


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
        "python_pkg.code_tutor._challenge_support.subprocess.run",
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
        "python_pkg.code_tutor._challenge_support.subprocess.run",
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
        "python_pkg.code_tutor._challenge_support.subprocess.run",
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
    with patch(
        "python_pkg.code_tutor._challenge_support._pytest_clean", return_value=True
    ):
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
        "python_pkg.code_tutor._challenge_support._pytest_clean", return_value=False
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

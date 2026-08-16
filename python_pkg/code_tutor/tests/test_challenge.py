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
    _project_root,
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

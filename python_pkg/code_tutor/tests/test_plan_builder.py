"""Tests for python_pkg.code_tutor._plan_builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from python_pkg.code_tutor._analyzer import CodeItem
from python_pkg.code_tutor._plan_builder import (
    _order_items,
    _session_title,
    _toposort_files,
    build_plan,
)


def _item(file: str, name: str = "fn", start: int = 1, end: int = 5) -> CodeItem:
    return CodeItem(
        id=f"{file}.{name}",
        file=file,
        type="function",
        name=name,
        start_line=start,
        end_line=end,
    )


# ---------------------------------------------------------------------------
# _toposort_files
# ---------------------------------------------------------------------------


def test_toposort_files_no_deps() -> None:
    a = Path("a.py")
    b = Path("b.py")
    deps = {a: set(), b: set()}
    result = _toposort_files(deps)
    assert set(result) == {a, b}


def test_toposort_files_with_deps() -> None:
    a = Path("a.py")
    b = Path("b.py")
    deps = {a: set(), b: {a}}
    result = _toposort_files(deps)
    assert result.index(a) < result.index(b)


def test_toposort_files_cycle() -> None:
    a = Path("a.py")
    b = Path("b.py")
    deps = {a: {b}, b: {a}}
    result = _toposort_files(deps)
    assert set(result) == {a, b}


# ---------------------------------------------------------------------------
# _order_items
# ---------------------------------------------------------------------------


def test_order_items_empty(tmp_path: Path) -> None:
    assert _order_items([], tmp_path) == []


def test_order_items_no_py_files(tmp_path: Path) -> None:
    items = [_item("main.go"), _item("lib.go")]
    result = _order_items(items, tmp_path)
    assert len(result) == 2


def test_order_items_py_files(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def fn(): pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a\ndef fn2(): pass\n", encoding="utf-8")
    items = [_item("a.py"), _item("b.py", name="fn2")]
    result = _order_items(items, tmp_path)
    assert len(result) == 2


def test_order_items_mixed(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    items = [_item("mod.py"), _item("script.go")]
    result = _order_items(items, tmp_path)
    assert len(result) == 2


def test_order_items_toposort_file_outside_codebase(tmp_path: Path) -> None:
    """A toposorted file outside the codebase root is skipped.

    Covers the ``is_relative_to`` False branch: an import can resolve to a
    path outside the codebase, which must not be added to the ordering map.
    """
    module = "python_pkg.code_tutor._plan_builder"
    outside = Path("/somewhere/else/x.py")
    items = [_item("a.py")]
    with (
        patch(f"{module}.get_python_files", return_value=[tmp_path / "a.py"]),
        patch(f"{module}.get_file_imports", return_value=set()),
        patch(f"{module}._toposort_files", return_value=[outside]),
    ):
        result = _order_items(items, tmp_path)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# _session_title
# ---------------------------------------------------------------------------


def test_session_title_empty() -> None:
    assert _session_title([]) == "untitled"


def test_session_title_single() -> None:
    items = [_item("src/main.py")]
    assert _session_title(items) == "src"


def test_session_title_same_dir() -> None:
    items = [_item("src/a.py"), _item("src/b.py")]
    assert _session_title(items) == "src"


def test_session_title_common_parent_root(tmp_path: Path) -> None:
    # parent of "src" is ".", so common becomes "."
    items = [_item("src/a.py"), _item("src/b/c.py")]
    result = _session_title(items)
    # common becomes "." because parent of "src" is Path(".")
    assert result == "a"


def test_session_title_common_parent_equals_common(tmp_path: Path) -> None:
    # dirs differ: common goes up from "pkg/sub" to parent "pkg"
    items = [_item("pkg/sub/a.py"), _item("pkg/sub/deeper/b.py")]
    result = _session_title(items)
    assert result == "pkg"


def test_session_title_deeper_common(tmp_path: Path) -> None:
    # Two items in different subdirs share a common parent that is not "."
    items = [_item("pkg/a/x.py"), _item("pkg/b/y.py")]
    result = _session_title(items)
    assert result == "pkg"


def test_session_title_root_files() -> None:
    # Both files at root level: parent = ".", common = "."
    items = [_item("a.py"), _item("b.py")]
    result = _session_title(items)
    assert result == "a"


# ---------------------------------------------------------------------------
# build_plan
# ---------------------------------------------------------------------------


def test_build_plan_basic(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    items = [_item("mod.py")]
    plan = build_plan(tmp_path, items)
    assert plan["total_items"] == 1
    assert len(plan["sessions"]) == 1
    assert "source_fingerprint" in plan


def test_build_plan_session_size(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn(): pass\n", encoding="utf-8")
    items = [_item("mod.py", name=f"fn{i}", start=i, end=i + 1) for i in range(5)]
    plan = build_plan(tmp_path, items, session_size=2)
    assert len(plan["sessions"]) == 3


def test_build_plan_empty_items(tmp_path: Path) -> None:
    plan = build_plan(tmp_path, [])
    assert plan["total_items"] == 0
    assert plan["sessions"] == []

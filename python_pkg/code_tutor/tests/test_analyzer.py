"""Tests for python_pkg.code_tutor._analyzer."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from unittest.mock import patch

from python_pkg.code_tutor._analyzer import (
    _extract_other,
    _extract_python,
    _FunctionVisitor,
    _is_binary,
    _make_id,
    _should_skip,
    extract_items,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# _is_binary
# ---------------------------------------------------------------------------


def test_is_binary_true(tmp_path: Path) -> None:
    f = tmp_path / "binary.bin"
    f.write_bytes(b"hello\x00world")
    assert _is_binary(f) is True


def test_is_binary_false(tmp_path: Path) -> None:
    f = tmp_path / "text.py"
    f.write_text("print('hello')", encoding="utf-8")
    assert _is_binary(f) is False


# ---------------------------------------------------------------------------
# _should_skip
# ---------------------------------------------------------------------------


def test_should_skip_dir(tmp_path: Path) -> None:
    assert _should_skip(".venv/lib/site-packages/foo.py") is True


def test_should_skip_node_modules(tmp_path: Path) -> None:
    assert _should_skip("node_modules/react/index.js") is True


def test_should_skip_suffix(tmp_path: Path) -> None:
    assert _should_skip("assets/logo.png") is True


def test_should_skip_false(tmp_path: Path) -> None:
    assert _should_skip("src/main.py") is False


def test_should_skip_pycache(tmp_path: Path) -> None:
    assert _should_skip("__pycache__/foo.pyc") is True


# ---------------------------------------------------------------------------
# _make_id
# ---------------------------------------------------------------------------


def test_make_id_basic() -> None:
    assert _make_id("src/utils.py", "helper") == "src.utils.helper"


def test_make_id_nested() -> None:
    assert _make_id("pkg/sub/mod.py", "fn") == "pkg.sub.mod.fn"


# ---------------------------------------------------------------------------
# _FunctionVisitor
# ---------------------------------------------------------------------------


def test_function_visitor_module_level() -> None:
    source = "def my_func(x):\n    return x\n"
    tree = ast.parse(source)
    visitor = _FunctionVisitor("mod.py")
    visitor.visit(tree)
    assert len(visitor.items) == 1
    item = visitor.items[0]
    assert item.name == "my_func"
    assert item.class_name == ""
    assert item.type == "function"


def test_function_visitor_class_method() -> None:
    source = "class Foo:\n    def bar(self):\n        pass\n"
    tree = ast.parse(source)
    visitor = _FunctionVisitor("mod.py")
    visitor.visit(tree)
    assert len(visitor.items) == 1
    item = visitor.items[0]
    assert item.name == "bar"
    assert item.class_name == "Foo"


def test_function_visitor_async() -> None:
    source = "async def do_thing():\n    pass\n"
    tree = ast.parse(source)
    visitor = _FunctionVisitor("mod.py")
    visitor.visit(tree)
    assert len(visitor.items) == 1
    assert visitor.items[0].type == "async_function"


def test_function_visitor_class_stack_restored() -> None:
    source = "class A:\n    def m(self): pass\nclass B:\n    def n(self): pass\n"
    tree = ast.parse(source)
    visitor = _FunctionVisitor("mod.py")
    visitor.visit(tree)
    names = {it.name: it.class_name for it in visitor.items}
    assert names["m"] == "A"
    assert names["n"] == "B"


# ---------------------------------------------------------------------------
# _extract_python
# ---------------------------------------------------------------------------


def test_extract_python_valid(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    f.write_text("def foo():\n    pass\n", encoding="utf-8")
    items = _extract_python(f, "mod.py")
    assert len(items) == 1
    assert items[0].name == "foo"


def test_extract_python_syntax_error(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("def (broken):\n", encoding="utf-8")
    items = _extract_python(f, "bad.py")
    assert items == []


# ---------------------------------------------------------------------------
# _extract_other
# ---------------------------------------------------------------------------


def test_extract_other_match(tmp_path: Path) -> None:
    f = tmp_path / "main.go"
    f.write_text("func doThing(x int) {\n}\n", encoding="utf-8")
    items = _extract_other(f, "main.go")
    assert any(it.name == "doThing" for it in items)


def test_extract_other_no_match(tmp_path: Path) -> None:
    f = tmp_path / "empty.go"
    f.write_text("package main\n", encoding="utf-8")
    items = _extract_other(f, "empty.go")
    assert items == []


def test_extract_other_oserror(tmp_path: Path) -> None:
    missing = tmp_path / "ghost.go"
    items = _extract_other(missing, "ghost.go")
    assert items == []


# ---------------------------------------------------------------------------
# extract_items
# ---------------------------------------------------------------------------


def test_extract_items_py_file(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def hello(): pass\n", encoding="utf-8")
    items = extract_items(tmp_path)
    assert any(it.name == "hello" for it in items)


def test_extract_items_other_lang(tmp_path: Path) -> None:
    (tmp_path / "main.go").write_text("func run(x int) {}\n", encoding="utf-8")
    items = extract_items(tmp_path)
    assert any(it.name == "run" for it in items)


def test_extract_items_skips_binary(tmp_path: Path) -> None:
    (tmp_path / "img.py").write_bytes(b"\x00\x01\x02\x03")
    items = extract_items(tmp_path)
    assert items == []


def test_extract_items_skips_should_skip(tmp_path: Path) -> None:
    skip_dir = tmp_path / ".venv"
    skip_dir.mkdir()
    (skip_dir / "lib.py").write_text("def x(): pass\n", encoding="utf-8")
    items = extract_items(tmp_path)
    assert items == []


def test_extract_items_skips_directories(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "mod.py").write_text("def f(): pass\n", encoding="utf-8")
    items = extract_items(tmp_path)
    assert any(it.name == "f" for it in items)


def test_extract_items_skips_unhandled_extension(tmp_path: Path) -> None:
    (tmp_path / "readme.txt").write_text("hello world", encoding="utf-8")
    items = extract_items(tmp_path)
    assert items == []


def test_extract_items_is_binary_oserror(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def f(): pass\n", encoding="utf-8")
    with patch(
        "python_pkg.code_tutor._analyzer._is_binary", side_effect=OSError("perm")
    ):
        items = extract_items(tmp_path)
    assert items == []

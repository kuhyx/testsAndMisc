"""Tests for python_pkg.code_tutor._analyzer."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

from python_pkg.code_tutor._analyzer import (
    CodeItem,
    _build_dotted_map,
    _extract_other,
    _extract_python,
    _FunctionVisitor,
    _is_binary,
    _make_id,
    _match_deps,
    _should_skip,
    codebase_fingerprint,
    extract_items,
    get_file_imports,
    get_python_files,
)

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


# ---------------------------------------------------------------------------
# get_python_files
# ---------------------------------------------------------------------------


def test_get_python_files(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2", encoding="utf-8")
    skip_dir = tmp_path / ".venv"
    skip_dir.mkdir()
    (skip_dir / "c.py").write_text("z = 3", encoding="utf-8")
    files = get_python_files(tmp_path)
    names = {f.name for f in files}
    assert "a.py" in names
    assert "b.py" in names
    assert "c.py" not in names


# ---------------------------------------------------------------------------
# _build_dotted_map
# ---------------------------------------------------------------------------


def test_build_dotted_map_normal(tmp_path: Path) -> None:
    f = tmp_path / "pkg" / "mod.py"
    f.parent.mkdir()
    f.write_text("x = 1", encoding="utf-8")
    result = _build_dotted_map(tmp_path, [f])
    assert result[f] == "pkg.mod"


def test_build_dotted_map_value_error(tmp_path: Path) -> None:
    other = tmp_path.parent / "other.py"
    result = _build_dotted_map(tmp_path, [other])
    assert other not in result


# ---------------------------------------------------------------------------
# _match_deps
# ---------------------------------------------------------------------------


def test_match_deps_exact(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    dotted_map = {f: "mod"}
    path = tmp_path / "main.py"
    result = _match_deps({"mod"}, dotted_map, path)
    assert f in result


def test_match_deps_prefix(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    dotted_map = {f: "mod"}
    path = tmp_path / "main.py"
    result = _match_deps({"pkg.mod"}, dotted_map, path)
    assert f in result


def test_match_deps_suffix(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    dotted_map = {f: "pkg.mod"}
    path = tmp_path / "main.py"
    result = _match_deps({"mod"}, dotted_map, path)
    assert f in result


def test_match_deps_excludes_self(tmp_path: Path) -> None:
    path = tmp_path / "mod.py"
    dotted_map = {path: "mod"}
    result = _match_deps({"mod"}, dotted_map, path)
    assert path not in result


def test_match_deps_no_match(tmp_path: Path) -> None:
    f = tmp_path / "other.py"
    dotted_map = {f: "other"}
    path = tmp_path / "main.py"
    result = _match_deps({"unrelated"}, dotted_map, path)
    assert f not in result


# ---------------------------------------------------------------------------
# Tests for get_file_imports
# ---------------------------------------------------------------------------


def test_get_file_imports_import(tmp_path: Path) -> None:
    f = tmp_path / "main.py"
    dep = tmp_path / "utils.py"
    f.write_text("import utils\n", encoding="utf-8")
    dep.write_text("x = 1", encoding="utf-8")
    result = get_file_imports(f, tmp_path, [f, dep])
    assert dep in result


def test_get_file_imports_from_import(tmp_path: Path) -> None:
    f = tmp_path / "main.py"
    dep = tmp_path / "utils.py"
    f.write_text("from utils import helper\n", encoding="utf-8")
    dep.write_text("def helper(): pass\n", encoding="utf-8")
    result = get_file_imports(f, tmp_path, [f, dep])
    assert dep in result


def test_get_file_imports_from_import_none_module(tmp_path: Path) -> None:
    # Relative import: node.module is None
    f = tmp_path / "main.py"
    f.write_text("from . import helper\n", encoding="utf-8")
    result = get_file_imports(f, tmp_path, [f])
    assert result == set()


def test_get_file_imports_syntax_error(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("def (broken):\n", encoding="utf-8")
    result = get_file_imports(f, tmp_path, [f])
    assert result == set()


# ---------------------------------------------------------------------------
# codebase_fingerprint
# ---------------------------------------------------------------------------


def test_codebase_fingerprint_basic(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    result = codebase_fingerprint(tmp_path)
    assert len(result) == 16
    assert result.isalnum()


def test_codebase_fingerprint_skips_dir(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    result = codebase_fingerprint(tmp_path)
    assert len(result) == 16


def test_codebase_fingerprint_skips_should_skip(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "lib.py").write_text("x = 1", encoding="utf-8")
    result_without = codebase_fingerprint(tmp_path)
    (tmp_path / "real.py").write_text("y = 2", encoding="utf-8")
    result_with = codebase_fingerprint(tmp_path)
    assert result_without != result_with


def test_codebase_fingerprint_stat_oserror(tmp_path: Path) -> None:
    (tmp_path / "source.py").write_text("x = 1", encoding="utf-8")

    stat_calls: dict[str, int] = {}
    real_stat = Path.stat

    def patched_stat(self: Path, **kwargs: object) -> object:
        key = str(self)
        stat_calls[key] = stat_calls.get(key, 0) + 1
        if stat_calls[key] >= 2 and key.endswith(".py"):
            msg = "simulated stat failure"
            raise OSError(msg)
        return real_stat(self, **kwargs)

    with patch.object(Path, "stat", patched_stat):
        result = codebase_fingerprint(tmp_path)

    assert len(result) == 16


def test_codebase_fingerprint_changes_on_modification(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    f.write_text("x = 1", encoding="utf-8")
    fp1 = codebase_fingerprint(tmp_path)
    f.write_text("x = 2", encoding="utf-8")
    fp2 = codebase_fingerprint(tmp_path)
    assert fp1 != fp2


def test_extract_items_image_suffix(tmp_path: Path) -> None:
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n")
    items = extract_items(tmp_path)
    assert items == []


def test_code_item_defaults() -> None:
    item = CodeItem(
        id="mod.fn",
        file="mod.py",
        type="function",
        name="fn",
        start_line=1,
        end_line=5,
    )
    assert item.class_name == ""
    assert item.depends_on == []


def test_codebase_fingerprint_stat_oserror_raises(tmp_path: Path) -> None:
    """Skip a file whose ``stat`` raises ``OSError`` (except branch).

    On this Python ``Path.is_file`` uses ``os.path.isfile`` rather than
    ``Path.stat``, so a stat that always fails for the source file reaches
    the ``except OSError`` handler that drops the unreadable entry.
    """
    (tmp_path / "source.py").write_text("x = 1", encoding="utf-8")
    real_stat = Path.stat

    def failing_stat(self: Path, **kwargs: object) -> object:
        """Raise for the target file, delegate to the real stat otherwise."""
        if str(self).endswith("source.py"):
            msg = "simulated stat failure"
            raise OSError(msg)
        return real_stat(self, **kwargs)

    with patch.object(Path, "stat", failing_stat):
        result = codebase_fingerprint(tmp_path)

    assert len(result) == 16

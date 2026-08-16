"""Tests for python_pkg.code_tutor._deps."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from python_pkg.code_tutor._analyzer import (
    CodeItem,
    extract_items,
)
from python_pkg.code_tutor._deps import (
    _build_dotted_map,
    _match_deps,
    codebase_fingerprint,
    get_file_imports,
    get_python_files,
)

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

    ``is_file()`` is forced True for the target so the loop reaches the
    explicit ``path.stat()`` at fingerprint time; that stat then raises and
    the ``except OSError`` handler drops the unreadable entry.  Patching both
    keeps this deterministic across Python versions (on some, ``is_file``
    itself calls ``stat`` and would otherwise re-raise before line reached).
    """
    (tmp_path / "source.py").write_text("x = 1", encoding="utf-8")
    real_stat = Path.stat
    real_is_file = Path.is_file

    def failing_stat(self: Path, **kwargs: object) -> object:
        """Raise for the target file, delegate to the real stat otherwise."""
        if str(self).endswith("source.py"):
            msg = "simulated stat failure"
            raise OSError(msg)
        return real_stat(self, **kwargs)

    def always_file(self: Path) -> bool:
        """Report the target as a regular file without calling stat."""
        return str(self).endswith("source.py") or real_is_file(self)

    with (
        patch.object(Path, "stat", failing_stat),
        patch.object(Path, "is_file", always_file),
    ):
        result = codebase_fingerprint(tmp_path)

    assert len(result) == 16

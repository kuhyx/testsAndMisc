"""Tests for storage locations and for the isolation guarantee itself."""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import paths

if TYPE_CHECKING:
    import pytest

_HOME_CAPTURING_CALLS = frozenset({"home", "expanduser", "getenv", "expandvars"})


def test_data_dir_follows_xdg_data_home(tmp_path: Path) -> None:
    assert paths.data_dir() == Path(os.environ["XDG_DATA_HOME"]) / "wsg_grabber"
    assert str(paths.data_dir()).startswith(str(tmp_path))


def test_data_dir_falls_back_to_dot_local_share(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    expected = Path.home() / ".local" / "share" / "wsg_grabber"
    assert paths.data_dir() == expected
    assert str(paths.data_dir()).startswith(str(tmp_path))


def test_derived_paths_live_under_the_data_dir() -> None:
    root = paths.data_dir()
    for candidate in (
        paths.db_path(),
        paths.incoming_dir(),
        paths.legacy_keep_dir(),
        paths.trash_dir(),
        paths.ipc_socket_path(),
    ):
        assert candidate.parent == root


def test_keep_dir_falls_back_to_downloads_without_the_cloud_folder() -> None:
    assert not paths.cloud_root().exists()
    assert paths.keep_dir() == Path.home() / "Downloads"


def test_keep_dir_uses_the_cloud_media_folder_for_this_year() -> None:
    paths.cloud_root().mkdir(parents=True)
    kept = paths.keep_dir()
    assert kept.parent.parent == paths.cloud_root() / "Media"
    assert kept.name == "wsg"
    assert kept.parent.name.isdigit()
    assert kept == paths.cloud_keep_dir(int(kept.parent.name))


def test_kept_candidates_cover_every_place_a_keep_can_end_up() -> None:
    media = paths.cloud_root() / "Media"
    for sub in ("2025/wsg", "2026/wsg", "2026/09", "2026/notes.txt"):
        (media / sub).parent.mkdir(parents=True, exist_ok=True)
    (media / "2025/wsg").mkdir(parents=True)
    (media / "2026/wsg").mkdir(parents=True)
    (media / "2026/09").mkdir(parents=True)
    (media / "2026/notes.txt").write_text("")
    candidates = paths.kept_candidates()
    assert candidates[0] == paths.keep_dir()
    assert candidates[1:3] == [media / "2025/wsg", media / "2026/wsg"]
    assert candidates[3:5] == [paths.legacy_keep_dir(), paths.downloads_dir()]
    assert candidates[5:] == [media / "2026/09"]


def test_socket_path_names_the_board() -> None:
    assert paths.ipc_socket_path().name == "mpv-wsg.sock"


def test_ensure_dirs_creates_every_directory() -> None:
    paths.ensure_dirs()
    for directory in (
        paths.data_dir(),
        paths.incoming_dir(),
        paths.keep_dir(),
        paths.trash_dir(),
    ):
        assert directory.is_dir()


def test_ensure_dirs_is_idempotent() -> None:
    paths.ensure_dirs()
    paths.ensure_dirs()
    assert paths.incoming_dir().is_dir()


def _module_level_home_calls(source: str) -> list[str]:
    """Return names of home-resolving calls made outside any function body.

    Args:
        source: Python source text of one module.

    Returns:
        list[str]: Offending attribute/function names, empty when the module is
        clean.
    """
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in tree.body:
        for inner in ast.walk(node):
            if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
        else:
            offenders.extend(_home_calls_in(node))
    return offenders


def _home_calls_in(node: ast.AST) -> list[str]:
    """Collect home-resolving call names anywhere beneath *node*.

    Args:
        node: AST node to scan.

    Returns:
        list[str]: Names such as ``home`` or ``expanduser``.
    """
    found: list[str] = []
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        func = inner.func
        name = func.attr if isinstance(func, ast.Attribute) else None
        if name is None and isinstance(func, ast.Name):
            name = func.id
        if name in _HOME_CAPTURING_CALLS:
            found.append(name)
    return found


def test_no_module_captures_a_home_directory_at_import_time() -> None:
    """Guard the whole package, not just paths.py.

    A constant like ``STATE = Path.home() / "x"`` is evaluated on import and
    can never be redirected afterwards, which is exactly how a previous package
    in this repo leaked test writes into real user data.
    """
    package_root = Path(paths.__file__).parent
    offenders: dict[str, list[str]] = {}
    for source_file in sorted(package_root.glob("*.py")):
        calls = _module_level_home_calls(source_file.read_text(encoding="utf-8"))
        if calls:
            offenders[source_file.name] = calls
    assert offenders == {}

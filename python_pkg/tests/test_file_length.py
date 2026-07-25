"""Test that all Python source files are at most 500 lines long."""

from __future__ import annotations

import os
from pathlib import Path

MAX_LINES = 500

# Directories to skip (vendored / generated).
#
# Virtual environments are NOT listed here by name: they are detected by their
# pyvenv.cfg marker instead, so any venv anyone drops in the tree is skipped
# whatever it is called. Naming them one by one is what broke this test before —
# `.venv` was listed but `.ci-mirror-venv` (created by the pre-push CI mirror)
# was not, and the walk then tripped over a third-party test fixture inside it.
_SKIP_DIRS = frozenset(
    {
        "__pycache__",
        "build",
        "dist",
        ".eggs",
        "node_modules",
        "sonic_pi",
        "third_party",  # vendored upstream MCP servers, skills and agents
        ".git",
    }
)

_ROOT = Path(__file__).resolve().parents[2]


def _is_venv(path: Path) -> bool:
    """Report whether a directory is a Python virtual environment.

    Args:
        path: Directory to inspect.

    Returns:
        True when the directory holds a ``pyvenv.cfg``, which every venv does.
    """
    return (path / "pyvenv.cfg").is_file()


def _python_files(root: Path) -> list[Path]:
    """Collect the project's own *.py files, pruning vendored trees and venvs.

    Args:
        root: Directory to walk.

    Returns:
        Every Python file under ``root`` that belongs to the project, sorted.
    """
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        # Mutating dirnames in place prunes the walk, so a venv's thousands of
        # third-party files are never visited at all.
        dirnames[:] = [
            name
            for name in dirnames
            if name not in _SKIP_DIRS and not _is_venv(current / name)
        ]
        files.extend(current / name for name in filenames if name.endswith(".py"))
    return sorted(files)


def _line_count(path: Path) -> int:
    """Count a file's lines without decoding it.

    Reading bytes keeps a line count from depending on the file's encoding: the
    repo vendors third-party fixtures that are deliberately not UTF-8, and
    decoding one of those used to fail this test with a UnicodeDecodeError.

    Args:
        path: File to measure.

    Returns:
        The number of lines in the file.
    """
    return len(path.read_bytes().splitlines())


def test_all_python_files_are_at_most_500_lines() -> None:
    """Every Python source file must be at most 500 lines."""
    violations: list[str] = []
    for path in _python_files(_ROOT):
        line_count = _line_count(path)
        if line_count > MAX_LINES:
            rel = path.relative_to(_ROOT)
            violations.append(f"  {rel}: {line_count} lines")

    assert not violations, (
        f"The following files exceed {MAX_LINES} lines:\n" + "\n".join(violations)
    )


def test_walk_skips_virtualenvs_whatever_they_are_named(tmp_path: Path) -> None:
    """A venv is pruned by its marker file, not by matching a known name."""
    package = tmp_path / "python_pkg"
    package.mkdir()
    own_source = package / "real_module.py"
    own_source.write_text("x = 1\n", encoding="utf-8")

    venv = tmp_path / "some-unlisted-venv"
    (venv / "lib").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    # Both of the traps the old walk fell into: far over the line limit, and not
    # decodable as UTF-8.
    (venv / "lib" / "vendored.py").write_bytes(b"# \xa4@\xa8\xc7\n" + b"pass\n" * 900)

    assert _python_files(tmp_path) == [own_source]


def test_line_count_survives_undecodable_bytes(tmp_path: Path) -> None:
    """Line counting works on a file that is not valid UTF-8."""
    path = tmp_path / "big5.py"
    path.write_bytes(b"# -*- coding: big5 -*-\n# \xa4@\xa8\xc7\npass\n")
    assert _line_count(path) == 3

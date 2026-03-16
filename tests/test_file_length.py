"""Test that all Python source files are at most 500 lines long."""

from __future__ import annotations

from pathlib import Path

MAX_LINES = 500

# Directories to skip (vendored / generated / virtual-envs)
_SKIP_DIRS = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".eggs",
        "node_modules",
        "sonic_pi",
        ".git",
    }
)

_ROOT = Path(__file__).resolve().parents[1]


def _python_files() -> list[Path]:
    """Collect every *.py file under the repo root, skipping vendored dirs."""
    files: list[Path] = []
    for path in _ROOT.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def test_all_python_files_are_at_most_500_lines() -> None:
    """Every Python source file must be at most 500 lines."""
    violations: list[str] = []
    for path in _python_files():
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_LINES:
            rel = path.relative_to(_ROOT)
            violations.append(f"  {rel}: {line_count} lines")

    assert not violations, (
        f"The following files exceed {MAX_LINES} lines:\n" + "\n".join(violations)
    )

"""Walking the codebase for Python files and mapping their import graph.

Split out of :mod:`python_pkg.code_tutor._analyzer` to keep it under the
250-line cap. Item extraction stays there; this module answers "which files
does this one depend on" and fingerprints the tree.
"""

from __future__ import annotations

import ast
import hashlib
from typing import TYPE_CHECKING

from python_pkg.code_tutor._analyzer import _should_skip

if TYPE_CHECKING:
    from pathlib import Path


def get_python_files(codebase: Path) -> list[Path]:
    """Return all non-skipped Python files under *codebase*.

    Args:
        codebase: Root directory to search.

    Returns:
        Sorted list of absolute Python file paths.
    """
    return [
        path
        for path in sorted(codebase.rglob("*.py"))
        if path.is_file() and not _should_skip(str(path.relative_to(codebase)))
    ]


def _build_dotted_map(codebase: Path, all_files: list[Path]) -> dict[Path, str]:
    """Build a mapping from file to its dotted module path relative to *codebase*.

    Args:
        codebase: Root directory used for relative path computation.
        all_files: All Python files within the codebase.

    Returns:
        Dict mapping each file in *all_files* to its dotted module string.
        Files that cannot be made relative to *codebase* are excluded.
    """
    result: dict[Path, str] = {}
    for f in all_files:
        try:
            rel = f.relative_to(codebase)
        except ValueError:
            continue
        result[f] = ".".join(rel.with_suffix("").parts)
    return result


def _match_deps(
    imported: set[str],
    dotted_map: dict[Path, str],
    path: Path,
) -> set[Path]:
    """Return the subset of *dotted_map* files that *path* appears to import.

    A file ``f`` is included when any imported module name equals, contains,
    or is contained by ``f``'s dotted path.

    Args:
        imported: Set of module name strings collected from import statements.
        dotted_map: Mapping of file to dotted module path.
        path: The file being analysed (excluded from its own dependency set).

    Returns:
        Set of dependency files.
    """
    deps: set[Path] = set()
    for imp in imported:
        for f, dotted in dotted_map.items():
            if f != path and (
                imp == dotted
                or imp.endswith("." + dotted)
                or dotted.endswith("." + imp)
            ):
                deps.add(f)
    return deps


def get_file_imports(path: Path, codebase: Path, all_files: list[Path]) -> set[Path]:
    """Parse Python imports and return the codebase files this file depends on.

    Uses a suffix-match heuristic: if an imported module name ends with (or
    matches) the dotted path of a file in *all_files*, that file is treated as
    a dependency.

    Args:
        path: The Python file to analyse.
        codebase: Root directory used for relative path computation.
        all_files: All Python files within the codebase.

    Returns:
        Subset of *all_files* that *path* imports from.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    dotted_map = _build_dotted_map(codebase, all_files)
    return _match_deps(imported, dotted_map, path)


def codebase_fingerprint(codebase: Path) -> str:
    """Compute a short fingerprint of all source files under *codebase*.

    Uses each file's mtime and size rather than content, so it is fast
    even on large repositories.  Returns a 16-character hex string that
    changes whenever any tracked file is added, removed, or modified.

    Args:
        codebase: Root directory of the codebase.

    Returns:
        16-character hex fingerprint string.
    """
    parts: list[str] = []
    for path in sorted(codebase.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(codebase))
        if _should_skip(rel):
            continue
        try:
            s = path.stat()
            parts.append(f"{rel}:{s.st_mtime_ns}:{s.st_size}")
        except OSError:
            pass
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]

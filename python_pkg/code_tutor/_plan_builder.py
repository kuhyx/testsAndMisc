"""Study plan construction: dependency ordering and session grouping."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from python_pkg.code_tutor._analyzer import (
    CodeItem,
    codebase_fingerprint,
    get_file_imports,
    get_python_files,
)


def _toposort_files(file_deps: dict[Path, set[Path]]) -> list[Path]:
    """Return files in topological order so dependencies come first.

    Args:
        file_deps: Mapping of file → set of files it depends on.

    Returns:
        Files ordered for learning (dependencies before dependents).
        Cycles are broken by appending remaining nodes in arbitrary order.
    """
    str_deps: dict[str, set[str]] = {
        str(k): {str(v) for v in vs} for k, vs in file_deps.items()
    }
    try:
        ordered_strs = list(TopologicalSorter(str_deps).static_order())
    except CycleError:
        ordered_strs = list(str_deps)
    return [Path(s) for s in ordered_strs]


def _order_items(items: list[CodeItem], codebase: Path) -> list[CodeItem]:
    """Sort *items* in dependency-first order.

    Python files are ordered by import relationships.  Other files are
    sorted by directory depth (shallowest first) then filename.

    Args:
        items: Unsorted list of code items.
        codebase: Root directory of the codebase.

    Returns:
        Items in recommended learning order.
    """
    if not items:
        return []

    py_files = get_python_files(codebase)
    py_rel_set: set[str] = set()
    file_order: dict[str, int] = {}

    if py_files:
        file_deps: dict[Path, set[Path]] = {
            f: get_file_imports(f, codebase, py_files) for f in py_files
        }
        ordered_files = _toposort_files(file_deps)
        for i, f in enumerate(ordered_files):
            if f.is_relative_to(codebase):
                rel = str(f.relative_to(codebase))
                file_order[rel] = i
                py_rel_set.add(rel)

    def _sort_key(item: CodeItem) -> tuple[int, int, str, int]:
        if item.file in py_rel_set:
            order = file_order.get(item.file, 9999)
        else:
            order = len(Path(item.file).parts) * 1000
        return (order, len(Path(item.file).parts), item.file, item.start_line)

    return sorted(items, key=_sort_key)


def _session_title(items: list[CodeItem]) -> str:
    """Derive a human-readable session title from items' file paths.

    Args:
        items: Items that will belong to the session.

    Returns:
        A short title string based on the common directory or first file stem.
    """
    if not items:
        return "untitled"
    dirs = [str(Path(it.file).parent) for it in items]
    common = dirs[0]
    for d in dirs[1:]:
        if d != common:
            parent = Path(common).parent
            common = "." if parent == Path() or str(parent) == common else str(parent)
    if common in {".", ""}:
        return Path(items[0].file).stem
    return Path(common).name or Path(items[0].file).stem


def build_plan(
    codebase: Path,
    items: list[CodeItem],
    *,
    session_size: int = 10,
) -> dict[str, object]:
    """Assemble a learning plan from extracted code items.

    Args:
        codebase: Root directory of the codebase.
        items: All extracted items (sorted internally by dependency order).
        session_size: Maximum number of items per session.

    Returns:
        Dict matching the ``plan.json`` schema ready for JSON serialisation.
    """
    ordered = _order_items(items, codebase)

    sessions: list[dict[str, object]] = []
    for session_idx in range(0, max(len(ordered), 1), session_size):
        chunk = ordered[session_idx : session_idx + session_size]
        if not chunk:
            break
        session_id = session_idx // session_size + 1
        sessions.append(
            {
                "id": session_id,
                "title": _session_title(chunk),
                "items": [dataclasses.asdict(it) for it in chunk],
            }
        )

    return {
        "codebase_path": str(codebase.resolve()),
        "created_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "total_items": len(ordered),
        "source_fingerprint": codebase_fingerprint(codebase),
        "sessions": sessions,
    }

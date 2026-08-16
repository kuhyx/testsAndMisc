"""Language-agnostic code item extraction from source files.

Supports Python via the ``ast`` module (exact line ranges) and other languages
via a regex heuristic.  Binary files and vendored directories are skipped.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from python_pkg.code_tutor._scan_tables import (
    _FUNCTION_RE,
    _OTHER_LANGS,
    _SKIP_DIRS,
    _SKIP_SUFFIXES,
)


@dataclass
class CodeItem:
    """A single extractable code unit (function or method).

    Attributes:
        id: Dotted identifier, e.g. ``module.submodule.function_name``.
        file: Relative path from the codebase root.
        type: ``"function"`` or ``"async_function"``.
        name: Bare function or method name.
        start_line: 1-based first line of the definition.
        end_line: 1-based last line of the definition.
        class_name: Enclosing class name, or ``""`` for module-level functions.
        depends_on: IDs of items that must be understood first.
    """

    id: str
    file: str
    type: str
    name: str
    start_line: int
    end_line: int
    class_name: str = ""
    depends_on: list[str] = field(default_factory=list)


def _is_binary(path: Path) -> bool:
    """Return True if *path* appears to be a binary file (null-byte heuristic).

    Uses the same heuristic as ``git`` and GNU ``grep``: a file is binary if
    its first 512 bytes contain a null byte.  Raises ``OSError`` on read
    failure so callers can handle unreadable files separately.

    Args:
        path: File to inspect.

    Returns:
        True when the first 512 bytes contain a null byte; False otherwise.

    Raises:
        OSError: When the file cannot be read.
    """
    chunk = path.read_bytes()[:512]
    return b"\x00" in chunk


def _should_skip(rel: str) -> bool:
    """Return True if this relative path should be excluded from analysis.

    Args:
        rel: Path relative to the codebase root.

    Returns:
        True when any path component is in ``_SKIP_DIRS`` or the file
        extension is in ``_SKIP_SUFFIXES``.
    """
    parts = Path(rel).parts
    if any(p in _SKIP_DIRS for p in parts):
        return True
    return Path(rel).suffix.lower() in _SKIP_SUFFIXES


def _make_id(rel_path: str, name: str) -> str:
    """Build a dotted item identifier from a relative path and function name.

    Args:
        rel_path: Path relative to the codebase root.
        name: Function or method name.

    Returns:
        Dotted identifier like ``module.submodule.function_name``.
    """
    without_ext = Path(rel_path).with_suffix("")
    return ".".join(without_ext.parts) + "." + name


class _FunctionVisitor(ast.NodeVisitor):
    """AST visitor that extracts function/method items with class context.

    Args:
        rel_path: Relative path of the file being visited.
    """

    def __init__(self, rel_path: str) -> None:
        """Initialise with file path and empty state."""
        self._rel_path = rel_path
        self._class_stack: list[str] = []
        self.items: list[CodeItem] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Push class name onto stack, recurse, then pop."""
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def _add(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
        end = getattr(node, "end_lineno", node.lineno)
        self.items.append(
            CodeItem(
                id=_make_id(self._rel_path, node.name),
                file=self._rel_path,
                type=kind,
                name=node.name,
                start_line=node.lineno,
                end_line=end,
                class_name=self._class_stack[-1] if self._class_stack else "",
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Record function and recurse into body."""
        self._add(node, "function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Record async function and recurse into body."""
        self._add(node, "async_function")
        self.generic_visit(node)


def _extract_python(path: Path, rel_path: str) -> list[CodeItem]:
    """Extract function/method items from a Python file using the AST.

    Args:
        path: Absolute path to the Python file.
        rel_path: Relative path used to build item IDs.

    Returns:
        List of ``CodeItem`` instances, one per function definition found.
        Returns an empty list on ``SyntaxError``.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    visitor = _FunctionVisitor(rel_path)
    visitor.visit(tree)
    return visitor.items


def _extract_other(path: Path, rel_path: str) -> list[CodeItem]:
    """Extract function-like items from non-Python files via regex.

    Scans each line for a function-definition keyword followed by an
    identifier and opening parenthesis.  End line is estimated at
    ``start + 40`` (clamped to file length).

    Args:
        path: Absolute path to the source file.
        rel_path: Relative path used to build item IDs.

    Returns:
        List of ``CodeItem`` instances.  Returns an empty list on ``OSError``.
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    items: list[CodeItem] = []
    for lineno, line in enumerate(lines, start=1):
        match = _FUNCTION_RE.match(line)
        if match:
            name = match.group(1)
            end = min(lineno + 40, len(lines))
            items.append(
                CodeItem(
                    id=_make_id(rel_path, name),
                    file=rel_path,
                    type="function",
                    name=name,
                    start_line=lineno,
                    end_line=end,
                )
            )
    return items


def extract_items(codebase: Path) -> list[CodeItem]:
    """Walk *codebase* and return all extractable code items.

    Args:
        codebase: Root directory to analyse.

    Returns:
        Flat list of ``CodeItem`` instances, unsorted.
    """
    items: list[CodeItem] = []
    for path in sorted(codebase.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(codebase))
        if _should_skip(rel):
            continue
        try:
            binary = _is_binary(path)
        except OSError:
            continue
        if binary:
            continue
        if path.suffix == ".py":
            items.extend(_extract_python(path, rel))
        elif path.suffix in _OTHER_LANGS:
            items.extend(_extract_other(path, rel))
    return items

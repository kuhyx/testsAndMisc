#!/usr/bin/env python3
"""Find every module the CI pytest run imports, for check_requirements_sync.

python-tests.yml installs only ``meta/requirements-test.txt`` and runs pytest
over the ``testpaths`` in ``meta/pyproject.toml``. The package-wide check
skips ``tests/`` directories and never looks at ``linux_configuration``, so a
test-only import (``hypothesis``) or a dependency of a script that
``linux_configuration/tests`` loads (``jeepney`` via ``game_rec_dbus``) passed
locally and failed CI with ``ModuleNotFoundError``.

This module walks the import closure instead: it starts from every ``.py``
file under the test paths (tests included) and follows bare first-party
imports into the repo's own modules, so only code the suite can actually
import is held to the test requirements.
"""

from __future__ import annotations

import ast
from collections import deque
from pathlib import Path
import sys

# Directories whose modules the suite can import by bare name: the testpaths'
# top-level trees plus meta/scripts (conftest puts it on sys.path).
_EXTRA_SEARCH_DIRS = ("meta/scripts",)


def _is_type_checking(node: ast.AST) -> bool:
    """Tell whether ``node`` is an ``if TYPE_CHECKING:`` block (never run)."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    name = test.attr if isinstance(test, ast.Attribute) else getattr(test, "id", "")
    return name == "TYPE_CHECKING"


def _imports(module: Path) -> set[str]:
    """Return the top-level names one file imports at runtime.

    Absolute imports only; imports under ``if TYPE_CHECKING:`` are skipped,
    because pytest never executes them.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    names: set[str] = set()
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".", 1)[0])
        stack.extend(
            child
            for child in ast.iter_child_nodes(node)
            if not _is_type_checking(child)
        )
    return names


def _local_index(search_dirs: list[Path]) -> dict[str, list[Path]]:
    """Map each importable first-party name to the files that define it.

    A ``name.py`` file defines ``name``; a directory with ``__init__.py``
    defines its own name with every file below it. A name defined twice maps
    to both, because which one wins depends on sys.path order.
    """
    index: dict[str, list[Path]] = {}
    for base in search_dirs:
        for path in sorted(base.rglob("*.py")):
            index.setdefault(path.stem, []).append(path)
            if path.name == "__init__.py":
                index.setdefault(path.parent.name, []).extend(
                    sorted(path.parent.rglob("*.py")),
                )
    index.pop("__init__", None)
    return index


def import_closure(root: Path, testpaths: list[str]) -> set[str]:
    """Return the non-stdlib, non-local names the test paths can import.

    Every file under each test path is a start point. A bare import that
    names a first-party module pulls that module's files into the walk;
    anything else outside the standard library is external.
    """
    starts = [root / path for path in testpaths]
    tops = {root / Path(path).parts[0] for path in testpaths}
    search = sorted(tops | {root / extra for extra in _EXTRA_SEARCH_DIRS})
    index = _local_index([path for path in search if path.is_dir()])
    queue = deque(path for start in starts for path in sorted(start.rglob("*.py")))
    seen: set[Path] = set()
    local = {top.name for top in tops}
    external: set[str] = set()
    while queue:
        module = queue.popleft()
        if module in seen:
            continue
        seen.add(module)
        for name in _imports(module):
            if name in index:
                local.add(name)
                queue.extend(index[name])
            elif name not in local and name not in sys.stdlib_module_names:
                external.add(name)
    return external

"""Lower-level helpers shared by the coding-challenge flows.

This module holds the test-discovery, pytest-execution and LLM
verdict/signature helpers used by :mod:`python_pkg.code_tutor._challenge`.
Splitting them out keeps each module comfortably under the repo's
500-line-per-file limit while preserving a clean, single-responsibility seam:
everything here is a stateless helper with no knowledge of the interactive
challenge flows that consume it.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import TYPE_CHECKING

from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem
    from python_pkg.code_tutor._llm import Backend


def _scan_test_file(source: str, item_name: str) -> list[str]:
    """Return pytest node IDs that reference *item_name*.

    Handles both module-level functions and class methods.  Class IDs use the
    ``ClassName::test_name`` format expected by pytest.

    Args:
        source: Full text of the test file.
        item_name: Name of the function under test.

    Returns:
        List of qualified pytest node IDs.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    src_lines = source.splitlines()
    matching: list[str] = []

    def _body_has(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        end = getattr(node, "end_lineno", node.lineno)
        return item_name in "\n".join(src_lines[node.lineno - 1 : end])

    for top in tree.body:
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if top.name.startswith("test_") and _body_has(top):
                matching.append(top.name)
        elif isinstance(top, ast.ClassDef):
            matching.extend(
                f"{top.name}::{method.name}"
                for method in top.body
                if (
                    isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and method.name.startswith("test_")
                    and _body_has(method)
                )
            )

    return matching


def _find_tests(item: CodeItem, codebase: Path) -> list[tuple[Path, list[str]]]:
    """Find existing test node IDs that reference *item.name* in *codebase*.

    Args:
        item: The code item being challenged.
        codebase: Root directory of the codebase to search.

    Returns:
        List of ``(test_file, [node_ids])`` pairs.
    """
    candidates = list(codebase.rglob("test_*.py")) + list(codebase.rglob("*_test.py"))
    results: list[tuple[Path, list[str]]] = []
    for test_file in sorted(set(candidates)):
        try:
            source = test_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if item.name not in source:
            continue
        node_ids = _scan_test_file(source, item.name)
        if node_ids:
            results.append((test_file, node_ids))
    return results


def _show_test_panels(
    test_entries: list[tuple[Path, list[str]]],
    console: Console,
) -> None:
    """Display each test function in a syntax-highlighted panel.

    Args:
        test_entries: List of ``(test_file, node_ids)`` pairs.
        console: Rich console for output.
    """
    for test_file, node_ids in test_entries:
        try:
            source = test_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        src_lines = source.splitlines()
        func_names = {nid.split("::")[-1] for nid in node_ids}
        for top in tree.body:
            nodes: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes = [(top.name, top)]
            elif isinstance(top, ast.ClassDef):
                for m in top.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nodes.append((m.name, m))
            for name, node in nodes:
                if name not in func_names:
                    continue
                end = getattr(node, "end_lineno", node.lineno)
                snippet = "\n".join(src_lines[node.lineno - 1 : end])
                console.print(
                    Panel(
                        Syntax(snippet, "python", theme="monokai", line_numbers=True),
                        title=f"[blue]Test: {name}[/blue]",
                        border_style="blue",
                    )
                )


def _collect_lines(
    prompt: str,
    console: Console,
    input_fn: Callable[[str], str],
) -> str | None:
    """Collect multi-line input until the user types END or skip.

    Args:
        prompt: Message to display before input begins.
        console: Rich console for output.
        input_fn: Callable for reading user input.

    Returns:
        The collected text as a single string, or ``None`` if skipped.
    """
    console.print(prompt)
    lines: list[str] = []
    while True:
        line = input_fn("")
        if line.strip().lower() == "skip":
            return None
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _project_root(start: Path) -> Path:
    """Walk up from *start* to find the nearest ``pyproject.toml`` / ``setup.py``.

    Args:
        start: Directory to begin the search from.

    Returns:
        Project root, or *start* if none found.
    """
    current = start.resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        current = current.parent
    return start.resolve()


def _pytest_clean(
    test_ids_or_file: list[str],
    project_root: Path,
    console: Console,
    extra_env: dict[str, str] | None = None,
) -> bool:
    """Run pytest on *test_ids_or_file* and return True if all pass.

    Coverage is disabled so the project's ``fail_under`` threshold does not
    interfere with isolated challenge runs.

    Args:
        test_ids_or_file: Pytest node IDs or a single temp-file path.
        project_root: Working directory for the pytest subprocess.
        console: Rich console for output.
        extra_env: Extra environment variables (e.g. PYTHONPATH override).

    Returns:
        ``True`` when all collected tests pass.
    """
    env = {**os.environ, **(extra_env or {})}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *test_ids_or_file,
            "-v",
            "--tb=short",
            "--no-header",
            "-p",
            "no:cov",
            "--override-ini=addopts=",
        ],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if output:
        console.print(output)
    return result.returncode == 0


def _patch_and_test(
    item: CodeItem,
    codebase_path: str,
    user_code: str,
    test_entries: list[tuple[Path, list[str]]],
    console: Console,
) -> bool:
    """Replace *item* in source with *user_code*, run tests, then restore.

    Args:
        item: Code item to patch.
        codebase_path: Absolute codebase root path.
        user_code: User's implementation text.
        test_entries: ``(test_file, node_ids)`` pairs to run.
        console: Rich console for output.

    Returns:
        ``True`` if all tests passed.
    """
    source_file = Path(codebase_path) / item.file
    original = source_file.read_text(encoding="utf-8")
    orig_lines = original.splitlines()

    before = orig_lines[: item.start_line - 1]
    after = orig_lines[item.end_line :]
    new_source = "\n".join(before + user_code.splitlines() + after) + "\n"

    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        console.print(f"[red]Syntax error in your implementation: {exc}[/red]")
        return False

    test_ids = [f"{tf}::{nid}" for tf, nids in test_entries for nid in nids]
    project_root = _project_root(Path(codebase_path))

    try:
        source_file.write_text(new_source, encoding="utf-8")
        return _pytest_clean(test_ids, project_root, console)
    finally:
        source_file.write_text(original, encoding="utf-8")


def _stream_verdict(
    system: str,
    user_msg: str,
    backend: Backend,
    console: Console,
    label: str = "Rating",
) -> str:
    """Stream an LLM call silently while showing an elapsed timer.

    Args:
        system: System prompt for the judge.
        user_msg: User message to judge.
        backend: LLM backend with a ``stream(system, user, callback)`` method.
        console: Rich console for the live timer.
        label: Label prefix shown in the timer (e.g. ``"Rating"``).

    Returns:
        Accumulated response text.
    """
    parts: list[str] = []
    start = time.monotonic()

    def _on_token(token: str) -> None:
        parts.append(token)
        elapsed = int(time.monotonic() - start)
        live.update(Text(f"{label}... {elapsed}s", style="yellow"))

    with Live(
        Text(f"{label}... 0s", style="yellow"),
        console=console,
        refresh_per_second=4,
        transient=True,
    ) as live:
        backend.stream(system, user_msg, _on_token)

    return "".join(parts)


def _parse_verdict(raw: str) -> tuple[str, str]:
    """Parse ``{"verdict": ..., "gap": ...}`` JSON from *raw*, tolerating fences.

    Args:
        raw: Raw LLM response text.

    Returns:
        ``(verdict, gap)`` where verdict is ``"PASS"`` or ``"FAIL"``.
    """
    clean = re.sub(r"```(?:json)?\s*", "", raw, flags=re.DOTALL).strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        return "FAIL", "Could not parse judge response."
    try:
        data = json.loads(clean[start:end])
    except json.JSONDecodeError:
        return "FAIL", "Could not parse judge response."
    verdict = str(data.get("verdict", "FAIL")).upper()
    if verdict not in {"PASS", "FAIL"}:
        verdict = "FAIL"
    return verdict, str(data.get("gap", ""))


# ---------------------------------------------------------------------------
# "Write tests first" flow -- helpers
# ---------------------------------------------------------------------------


def _extract_signature_block(item: CodeItem, codebase_path: str) -> str:
    """Return the function signature plus docstring, without the body.

    Gives the user the contract of the function so they can write tests
    without seeing the implementation.

    Args:
        item: Code item to extract from.
        codebase_path: Absolute codebase root path.

    Returns:
        Multi-line string ending after the closing ``\"\"\"`` of the docstring,
        or just the ``def`` line when no docstring is present.
    """
    path = Path(codebase_path) / item.file
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return f"def {item.name}(...):"

    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != item.name:
            continue
        sig_end = node.lineno
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            sig_end = getattr(node.body[0], "end_lineno", node.lineno + 1)
        return "\n".join(lines[node.lineno - 1 : sig_end])

    return f"def {item.name}(...):"


def _import_hint(item: CodeItem, codebase_path: str, project_root: Path) -> str:
    """Build the Python import statement for *item*.

    Args:
        item: Code item to import.
        codebase_path: Absolute codebase root path.
        project_root: Project root (where pyproject.toml lives).

    Returns:
        A ``from <module> import <name>`` string.
    """
    abs_file = (Path(codebase_path) / item.file).resolve()
    try:
        rel = abs_file.relative_to(project_root).with_suffix("")
        module = ".".join(rel.parts)
    except ValueError:
        module = Path(item.file).stem
    return f"from {module} import {item.name}"

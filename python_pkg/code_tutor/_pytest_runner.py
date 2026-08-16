"""Running the user's tests in an isolated pytest subprocess.

Split out of :mod:`python_pkg.code_tutor._challenge_support` to keep it under
the 250-line cap. ``_challenge`` imports both entry points back, because
``tests/test_challenge_part3.py`` patches them on that module.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING

from python_pkg.code_tutor._challenge_support import _project_root

if TYPE_CHECKING:
    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem


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

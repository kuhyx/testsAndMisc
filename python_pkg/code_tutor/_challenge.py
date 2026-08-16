"""Coding challenge: reproduce a function from scratch, validated by tests.

After a PASS verdict the user is offered a challenge: rewrite the function
without seeing its body, validated either by existing tests or by tests they
write themselves.

If existing tests exist for the function -> show them, ask user to implement.
If no tests exist -> ask user to write tests first, rate them, then ask user
to implement.

In both cases the original implementation is hidden during the challenge.

The lower-level discovery / pytest / verdict helpers live in
:mod:`python_pkg.code_tutor._challenge_support`, and the two flows plus the
public ``run_coding_challenge`` entry point in
:mod:`python_pkg.code_tutor._challenge_flows`. This module keeps the three
interactive stages those flows are built from.
"""

from __future__ import annotations

import ast
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.syntax import Syntax

from python_pkg.code_tutor._challenge_prompts import (
    _MAX_TEST_ATTEMPTS,
    _TEST_JUDGE_SYSTEM,
)
from python_pkg.code_tutor._challenge_support import (
    _collect_lines,
    _extract_signature_block,
    _project_root,
)
from python_pkg.code_tutor._pytest_runner import _pytest_clean
from python_pkg.code_tutor._verdict import _parse_verdict, _stream_verdict

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem
    from python_pkg.code_tutor._llm import Backend


def _validate_tests_against_real(
    test_code: str,
    import_header: str,
    project_root: Path,
    console: Console,
) -> bool:
    """Write *test_code* to a temp file and run it against the real implementation.

    If the tests fail on the real (correct) implementation, they are wrong.

    Args:
        test_code: The user's pytest test code.
        import_header: Auto-generated import line prepended to the test file.
        project_root: Project root used for PYTHONPATH and cwd.
        console: Rich console for output.

    Returns:
        ``True`` when all tests pass on the real implementation.
    """
    full_code = import_header + "\n\n" + test_code
    try:
        ast.parse(full_code)
    except SyntaxError as exc:
        console.print(f"[red]Syntax error in your tests: {exc}[/red]")
        return False

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_ct_test.py",
        dir=None,
        delete=False,
        encoding="utf-8",
    ) as fh:
        fh.write(full_code)
        temp_path = Path(fh.name)

    try:
        return _pytest_clean(
            [str(temp_path)],
            project_root,
            console,
            extra_env={"PYTHONPATH": str(project_root)},
        )
    finally:
        temp_path.unlink(missing_ok=True)


def _collect_and_rate_tests(
    sig_block: str,
    user_explanation: str,
    backend: Backend,
    console: Console,
    input_fn: Callable[[str], str],
) -> str | None:
    """Prompt the user to write tests and rate them up to *_MAX_TEST_ATTEMPTS* times.

    Args:
        sig_block: Function signature + docstring shown as context.
        user_explanation: Student's earlier explanation (shown as reference).
        backend: LLM backend for test quality rating.
        console: Rich console for output.
        input_fn: Callable for reading user input.

    Returns:
        The approved test code string, or ``None`` if the user skipped.
    """
    for attempt in range(1, _MAX_TEST_ATTEMPTS + 1):
        collected = _collect_lines(
            f"\n[bold]Write your tests (attempt {attempt}/{_MAX_TEST_ATTEMPTS}).[/bold]"
            "  Finish with [dim]END[/dim] on a blank line,"
            " or [dim]skip[/dim] to exit.",
            console,
            input_fn,
        )
        if collected is None:
            console.print("[yellow]Challenge skipped.[/yellow]")
            return None

        sig_and_exp = (
            f"Function contract:\n{sig_block}"
            f"\n\nStudent explanation:\n{user_explanation}"
        )
        raw = _stream_verdict(
            _TEST_JUDGE_SYSTEM,
            f"{sig_and_exp}\n\nStudent's tests:\n{collected}",
            backend,
            console,
            label="Rating tests",
        )
        verdict, gap = _parse_verdict(raw)

        if verdict == "PASS":
            return collected

        console.print(f"[red]Tests need improvement[/red] -- {gap}")
        if attempt == _MAX_TEST_ATTEMPTS:
            console.print(
                f"[yellow]Skipping challenge after"
                f" {_MAX_TEST_ATTEMPTS} attempts.[/yellow]"
            )
            return None
        console.print("Try again with better coverage:\n")
    return None  # pragma: no cover - loop always returns on the final attempt


def _run_user_impl(
    item: CodeItem,
    codebase_path: str,
    test_code: str,
    import_hint: str,
    console: Console,
    input_fn: Callable[[str], str],
) -> str:
    """Prompt user to write an implementation and run it against *test_code*.

    Patches the source file, runs a temp test file, then always restores.

    Args:
        item: Code item to implement.
        codebase_path: Absolute codebase root path.
        test_code: Approved test code (without import header).
        import_hint: Auto-generated import line prepended to the test file.
        console: Rich console for output.
        input_fn: Callable for reading user input.

    Returns:
        ``"passed"``, ``"failed"``, or ``"skipped"``.
    """
    project_root = _project_root(Path(codebase_path))
    sig_block = _extract_signature_block(item, codebase_path)
    console.print(
        Panel(
            Syntax(sig_block, "python", theme="monokai"),
            title="[blue]Function signature (implement this)[/blue]",
            border_style="blue",
        )
    )
    user_impl = _collect_lines(
        f"\n[bold]Now write the implementation of [cyan]{item.name}[/cyan].[/bold]"
        "  Finish with [dim]END[/dim] on a blank line, or [dim]skip[/dim] to exit.",
        console,
        input_fn,
    )
    if user_impl is None:
        console.print("[yellow]Challenge skipped.[/yellow]")
        return "skipped"

    try:
        ast.parse(user_impl)
    except SyntaxError as exc:
        console.print(f"[red]Syntax error in your implementation: {exc}[/red]")
        return "failed"

    full_test_code = import_hint + "\n\n" + test_code
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_ct_test.py", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(full_test_code)
        temp_path = Path(fh.name)

    source_file = Path(codebase_path) / item.file
    original = source_file.read_text(encoding="utf-8")
    orig_lines = original.splitlines()
    before = orig_lines[: item.start_line - 1]
    after = orig_lines[item.end_line :]
    new_source = "\n".join(before + user_impl.splitlines() + after) + "\n"

    try:
        source_file.write_text(new_source, encoding="utf-8")
        passed = _pytest_clean(
            [str(temp_path)],
            project_root,
            console,
            extra_env={"PYTHONPATH": str(project_root)},
        )
    finally:
        source_file.write_text(original, encoding="utf-8")
        temp_path.unlink(missing_ok=True)

    if passed:
        console.print(
            "[green bold]✓ All your tests passed"
            " -- you can write it and test it![/green bold]"
        )
        return "passed"
    console.print("[red]✗ Your implementation didn't pass your own tests.[/red]")
    return "failed"

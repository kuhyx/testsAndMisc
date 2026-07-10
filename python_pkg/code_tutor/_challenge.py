"""Coding challenge: reproduce a function from scratch, validated by tests.

After a PASS verdict the user is offered a challenge: rewrite the function
without seeing its body, validated either by existing tests or by tests they
write themselves.

If existing tests exist for the function -> show them, ask user to implement.
If no tests exist -> ask user to write tests first, rate them, then ask user
to implement.

In both cases the original implementation is hidden during the challenge.

The lower-level discovery / pytest / verdict helpers live in
:mod:`python_pkg.code_tutor._challenge_support`; this module keeps the
interactive validation, rating and flow orchestration plus the public
``run_coding_challenge`` entry point.
"""

from __future__ import annotations

import ast
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.syntax import Syntax

from python_pkg.code_tutor._challenge_support import (
    _collect_lines,
    _extract_signature_block,
    _find_tests,
    _import_hint,
    _parse_verdict,
    _patch_and_test,
    _project_root,
    _pytest_clean,
    _show_test_panels,
    _stream_verdict,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem
    from python_pkg.code_tutor._llm import Backend

_NO_AI_NOTICE = (
    "[bold yellow]⚠  No AI assistance -- write this yourself.[/bold yellow]\n"
    "Your own explanation (and the tests below) are your only reference."
)

_MAX_TEST_ATTEMPTS = 2

_TEST_JUDGE_SYSTEM = (
    "You are a code tutor evaluating whether a student's tests adequately"
    " cover a function.\n\n"
    "PASS if the tests:\n"
    "  - Include at least 2 meaningfully different test cases with distinct inputs\n"
    "  - Use assertions that verify the actual return value or observable behavior\n"
    "  - Would catch an obviously wrong implementation (e.g. one that always"
    ' returns "")\n\n'
    "FAIL only if:\n"
    "  - There is only one trivial test case\n"
    "  - Assertions are always-true or don't check the function's real output\n"
    "  - All tests are essentially the same scenario with trivially different data\n\n"
    "Do NOT require error/edge-case tests for pure transformation functions that"
    " have no error handling.  2+ meaningful happy-path cases with distinct"
    " inputs is enough.\n\n"
    "Respond with valid JSON only, no other text:\n"
    '{"verdict": "PASS" | "FAIL",'
    ' "gap": "<one sentence on the specific missing scenario,'
    ' or empty string on PASS>"}'
)


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


# ---------------------------------------------------------------------------
# "Write tests first" flow -- orchestrator
# ---------------------------------------------------------------------------


def _write_tests_first_flow(
    item: CodeItem,
    codebase_path: str,
    user_explanation: str,
    backend: Backend,
    console: Console,
    input_fn: Callable[[str], str],
) -> str:
    """Challenge flow used when no existing tests are found.

    Asks the user to write tests first, rates them with the LLM, validates
    them against the real implementation, then asks the user to write their
    own implementation.

    Args:
        item: Code item being challenged.
        codebase_path: Absolute codebase root path.
        user_explanation: User's earlier explanation, shown as reference.
        backend: LLM backend for test quality rating.
        console: Rich console for output.
        input_fn: Callable for reading user input.

    Returns:
        ``"passed"``, ``"failed"``, or ``"skipped"``.
    """
    project_root = _project_root(Path(codebase_path))
    import_hint = _import_hint(item, codebase_path, project_root)
    sig_block = _extract_signature_block(item, codebase_path)

    console.print(
        "\n[bold cyan]Coding challenge (tests first):[/bold cyan] "
        "No existing tests found -- write them before implementing.\n"
    )
    answer = input_fn("Take the challenge? [y/N] ").strip().lower()
    if answer != "y":
        return "skipped"

    console.print(
        Panel(
            user_explanation,
            title="Your explanation (your only reference)",
            border_style="dim",
        )
    )
    console.print(_NO_AI_NOTICE)
    console.print(
        Panel(
            Syntax(sig_block, "python", theme="monokai"),
            title="[blue]Function signature + contract[/blue]",
            border_style="blue",
        )
    )
    console.print(
        f"\n[dim]Auto-import that will be prepended to your tests:[/dim]\n"
        f"[cyan]{import_hint}[/cyan]\n"
        "[dim]Add any other imports (pytest, MagicMock, etc.) yourself.[/dim]\n"
    )

    test_code = _collect_and_rate_tests(
        sig_block, user_explanation, backend, console, input_fn
    )
    if test_code is None:
        return "skipped"

    console.print(
        "\n[dim]Validating your tests against the real implementation...[/dim]"
    )
    if not _validate_tests_against_real(test_code, import_hint, project_root, console):
        console.print(
            "[red]Your tests fail on the correct implementation -- "
            "they may be testing the wrong behavior.  Skipping.[/red]"
        )
        return "skipped"

    console.print(
        "[green]Tests look good -- they pass on the real implementation.[/green]"
    )
    return _run_user_impl(
        item, codebase_path, test_code, import_hint, console, input_fn
    )


# ---------------------------------------------------------------------------
# "Existing tests" flow
# ---------------------------------------------------------------------------


def _existing_tests_flow(
    item: CodeItem,
    codebase_path: str,
    user_explanation: str,
    test_entries: list[tuple[Path, list[str]]],
    console: Console,
    input_fn: Callable[[str], str],
) -> str:
    """Challenge flow used when existing tests are found.

    Shows the tests, asks user to implement from scratch.

    Args:
        item: Code item being challenged.
        codebase_path: Absolute codebase root path.
        user_explanation: User's earlier explanation.
        test_entries: Existing test file/node-id pairs.
        console: Rich console for output.
        input_fn: Callable for reading user input.

    Returns:
        ``"passed"``, ``"failed"``, or ``"skipped"``.
    """
    n_tests = sum(len(ids) for _, ids in test_entries)
    console.print(
        "\n[bold cyan]Coding challenge:[/bold cyan] "
        f"Can you rewrite this function from scratch? "
        f"[dim]({n_tests} test(s) will validate it)[/dim]"
    )
    answer = input_fn("Take the challenge? [y/N] ").strip().lower()
    if answer != "y":
        return "skipped"

    console.print(
        Panel(
            user_explanation,
            title="Your explanation (your only reference)",
            border_style="dim",
        )
    )
    console.print(_NO_AI_NOTICE)
    _show_test_panels(test_entries, console)

    user_code = _collect_lines(
        f"\n[bold]Write [cyan]{item.name}[/cyan] from scratch.[/bold]  "
        "Finish with [dim]END[/dim] on a blank line, or [dim]skip[/dim] to skip.",
        console,
        input_fn,
    )
    if user_code is None:
        console.print("[yellow]Challenge skipped.[/yellow]")
        return "skipped"

    console.print("\n[dim]Running tests against your implementation...[/dim]")
    passed = _patch_and_test(item, codebase_path, user_code, test_entries, console)

    if passed:
        console.print(
            "[green bold]✓ All tests passed -- you really understand it![/green bold]"
        )
        return "passed"
    console.print("[red]✗ Some tests failed -- try again next session.[/red]")
    return "failed"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_coding_challenge(
    item: CodeItem,
    codebase_path: str,
    user_explanation: str,
    backend: Backend,
    console: Console,
    input_fn: Callable[[str], str] = input,
) -> str:
    """Offer the user a coding challenge after a PASS verdict.

    Routes to one of two flows:
    - **Existing tests found**: show tests, user writes implementation.
    - **No tests found**: user writes tests first (LLM-rated), then implementation.

    Only offered for ``.py`` files.

    Args:
        item: The code item to challenge on.
        codebase_path: Absolute path of the codebase root.
        user_explanation: The explanation the user gave during the lesson.
        backend: LLM backend (used for test quality rating in the no-tests flow).
        console: Rich console for output.
        input_fn: Callable for reading user input.

    Returns:
        ``"passed"``, ``"failed"``, or ``"skipped"``.
    """
    if not item.file.endswith(".py"):
        return "skipped"

    codebase = Path(codebase_path)
    test_entries = _find_tests(item, codebase)

    if test_entries:
        return _existing_tests_flow(
            item, codebase_path, user_explanation, test_entries, console, input_fn
        )
    return _write_tests_first_flow(
        item, codebase_path, user_explanation, backend, console, input_fn
    )

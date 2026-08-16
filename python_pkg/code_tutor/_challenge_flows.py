"""The two challenge flows and the entry point that picks between them.

Split out of :mod:`python_pkg.code_tutor._challenge` to keep it under the
250-line cap. The three stage helpers stay there and are imported back, because
``tests/test_challenge_part3.py`` patches them on ``_challenge``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.syntax import Syntax

from python_pkg.code_tutor._challenge import (
    _collect_and_rate_tests,
    _run_user_impl,
    _validate_tests_against_real,
)
from python_pkg.code_tutor._challenge_prompts import _NO_AI_NOTICE
from python_pkg.code_tutor._challenge_support import (
    _collect_lines,
    _extract_signature_block,
    _find_tests,
    _import_hint,
    _project_root,
    _show_test_panels,
)
from python_pkg.code_tutor._pytest_runner import _patch_and_test

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem
    from python_pkg.code_tutor._llm import Backend


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

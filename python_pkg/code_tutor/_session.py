"""Interactive study session orchestrator.

Thin coordination layer: loads plan + progress, calls the Verifier per item,
saves progress after each lesson, and shows a summary table at the end.
No LLM calls or judgment logic live here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from rich.table import Table

from python_pkg.code_tutor._progress import (
    append_session_record,
    item_from_data,
    load_plan,
    load_progress,
    save_progress,
)
from python_pkg.code_tutor._verifier import Verifier

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem
    from python_pkg.code_tutor._llm import Backend
    from python_pkg.code_tutor._progress import PlanData, ProgressData


def _items_from_plan(plan: PlanData) -> list[CodeItem]:
    """Reconstruct ``CodeItem`` objects from a loaded ``PlanData`` dict.

    Args:
        plan: Plan as loaded from ``plan.json``.

    Returns:
        Flat list of ``CodeItem`` instances in session order.
    """
    return [
        item_from_data(data)
        for session in plan["sessions"]
        for data in session["items"]
    ]


def _show_summary(
    results: dict[str, list[str]],
    console: Console,
) -> None:
    """Print a session summary table to *console*.

    Args:
        results: Mapping of outcome (``"learned"``, ``"struggled"``,
            ``"skipped"``) to lists of item IDs.
        console: Rich console for output.
    """
    table = Table(title="Session summary", show_header=True, header_style="bold")
    table.add_column("Outcome")
    table.add_column("Count", justify="right")
    table.add_row("[green]Learned[/green]", str(len(results.get("learned", []))))
    table.add_row("[red]Struggled[/red]", str(len(results.get("struggled", []))))
    table.add_row("[yellow]Skipped[/yellow]", str(len(results.get("skipped", []))))
    console.print(table)


def run_session(
    codebase: Path,
    backend: Backend,
    *,
    console: Console,
    input_fn: Callable[[str], str] = input,
) -> None:
    """Run an interactive study session for *codebase*.

    Loads the saved plan and progress, iterates over unfinished items, calls
    the Verifier per item, saves progress after each lesson, and shows a
    summary table on completion.

    Args:
        codebase: Root directory of the codebase being studied.
        backend: LLM backend to pass to the Verifier.
        console: Rich console for all output.
        input_fn: Callable used for user input (injectable for testing).
    """
    plan = load_plan(codebase)
    if plan is None:
        console.print(
            "[red]No plan found. "
            "Run [bold]code_tutor analyze <path>[/bold] first.[/red]"
        )
        return

    progress: ProgressData = load_progress(codebase)
    done_ids: set[str] = (
        set(progress["learned"]) | set(progress["struggled"]) | set(progress["skipped"])
    )

    all_items = _items_from_plan(plan)
    pending = [it for it in all_items if it.id not in done_ids]

    if not pending:
        console.print(
            "[green]All items complete!  "
            "Run [bold]code_tutor status[/bold] to see your progress.[/green]"
        )
        return

    verifier = Verifier(backend, console)
    results: dict[str, list[str]] = {"learned": [], "struggled": [], "skipped": []}
    codebase_str = str(codebase.resolve())

    for item in pending:
        record = verifier.run_lesson(item, codebase_str, input_fn=input_fn)
        outcome = record.outcome
        results[outcome].append(item.id)
        append_session_record(codebase, record)
        if outcome == "learned":
            progress["learned"].append(item.id)
        elif outcome == "struggled":
            progress["struggled"].append(item.id)
        else:
            progress["skipped"].append(item.id)
        progress["last_session"] = datetime.now(tz=timezone.utc).isoformat(
            timespec="seconds"
        )
        save_progress(codebase, progress)

    _show_summary(results, console)

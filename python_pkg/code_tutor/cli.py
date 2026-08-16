"""CLI entry point for code_tutor.

Commands:
    analyze  -- walk a codebase and produce a study plan
    study    -- run (or resume) an interactive study session
    status   -- show progress dashboard
    drill    -- force a lesson on a specific file
"""

from __future__ import annotations

from pathlib import Path
import sys

import requests
from rich.console import Console
from rich.table import Table
import typer

from python_pkg.code_tutor._analyzer import extract_items
from python_pkg.code_tutor._cli_checks import (
    _ensure_fresh_plan,
    _ensure_ollama_running,
    _find_codebase_for_file,
)
from python_pkg.code_tutor._llm import OllamaBackend
from python_pkg.code_tutor._plan_builder import build_plan
from python_pkg.code_tutor._progress import (
    append_session_record,
    config_dir,
    item_from_data,
    load_plan,
    load_progress,
    save_plan,
)
from python_pkg.code_tutor._session import run_session
from python_pkg.code_tutor._verifier import Verifier

app = typer.Typer(help="Socratic codebase understanding tutor.")
_console = Console()

_OLLAMA_API = "http://localhost:11434/api/tags"
_OLLAMA_START_TIMEOUT = 30


@app.command()
def analyze(
    codebase: Path = typer.Argument(
        ..., help="Root directory of the codebase to study."
    ),
    session_size: int = typer.Option(10, help="Items per study session."),
) -> None:
    """Analyse *codebase* and create a dependency-ordered study plan.

    The plan is saved to ``~/.config/code_tutor/<hash>/plan.json``.

    Args:
        codebase: Root directory of the codebase.
        session_size: Maximum number of items per study session.
    """
    if not codebase.is_dir():
        _console.print(f"[red]Error: {codebase} is not a directory.[/red]")
        raise typer.Exit(1)

    _console.print(f"Analysing [bold]{codebase}[/bold] ...")
    items = extract_items(codebase)

    if not items:
        _console.print("[yellow]No extractable items found in this directory.[/yellow]")
        raise typer.Exit(0)

    n_items = len(items)
    plan = build_plan(codebase, items, session_size=session_size)
    save_plan(codebase, plan)

    n_sessions = (n_items + session_size - 1) // session_size
    dest = config_dir(codebase) / "plan.json"
    _console.print(
        f"Found [bold]{n_items}[/bold] items across {n_sessions} session(s).\n"
        f"Plan saved to [dim]{dest}[/dim]"
    )


@app.command()
def study(
    codebase: Path = typer.Argument(
        Path(),
        help="Root directory of the codebase.  Defaults to the current directory.",
    ),
) -> None:
    """Start or resume an interactive study session for *codebase*.

    Automatically rebuilds the plan if source files have changed since the last
    analyze run.  Starts Ollama via systemctl if it is not already running.

    Args:
        codebase: Root directory of the codebase.
    """
    if not codebase.is_dir():
        _console.print(f"[red]Error: {codebase} is not a directory.[/red]")
        raise typer.Exit(1)

    plan = load_plan(codebase)
    if plan is None:
        _console.print(
            "[yellow]No plan found.  "
            "Run [bold]code_tutor analyze <path>[/bold] first.[/yellow]"
        )
        raise typer.Exit(1)

    _ensure_fresh_plan(codebase, plan, _console)

    if not _ensure_ollama_running(_console):
        raise typer.Exit(1)

    backend = OllamaBackend()
    try:
        run_session(codebase, backend, console=_console)
    except requests.exceptions.ConnectionError as exc:
        _console.print(
            "[red]Cannot connect to Ollama.  Is it running at localhost:11434?[/red]"
        )
        raise typer.Exit(1) from exc


@app.command()
def status(
    codebase: Path = typer.Argument(
        Path(),
        help="Root directory of the codebase.",
    ),
) -> None:
    """Show a progress dashboard for *codebase*.

    Automatically rebuilds the plan if source files have changed.

    Args:
        codebase: Root directory of the codebase.
    """
    plan = load_plan(codebase)
    if plan is None:
        _console.print(
            "[yellow]No plan found.  "
            "Run [bold]code_tutor analyze <path>[/bold] first.[/yellow]"
        )
        raise typer.Exit(1)

    plan = _ensure_fresh_plan(codebase, plan, _console)

    progress = load_progress(codebase)
    total = plan["total_items"]
    learned = len(progress["learned"])
    struggled = len(progress["struggled"])
    skipped = len(progress["skipped"])
    remaining = total - learned - struggled - skipped

    table = Table(title=f"Progress: {codebase}", show_header=True, header_style="bold")
    table.add_column("Category")
    table.add_column("Count", justify="right")
    table.add_row("[green]Learned[/green]", str(learned))
    table.add_row("[red]Struggled[/red]", str(struggled))
    table.add_row("[yellow]Skipped[/yellow]", str(skipped))
    table.add_row("Remaining", str(remaining))
    table.add_row("[bold]Total[/bold]", str(total))
    _console.print(table)


@app.command()
def drill(
    file: Path = typer.Argument(..., help="Source file to drill."),
) -> None:
    """Force a study lesson on every item in *file*.

    Searches all saved plans to find which codebase contains *file*.
    Automatically rebuilds the plan if source files have changed.
    Starts Ollama via systemctl if it is not already running.

    Args:
        file: Absolute or relative path to the source file.
    """
    file = file.resolve()
    codebase = _find_codebase_for_file(file)
    if codebase is None:
        _console.print(
            "[red]No saved plan contains this file.  "
            "Run [bold]code_tutor analyze <codebase>[/bold] first.[/red]"
        )
        raise typer.Exit(1)

    plan = load_plan(codebase)
    if plan is None:
        _console.print("[red]Plan disappeared unexpectedly.[/red]")
        raise typer.Exit(1)

    plan = _ensure_fresh_plan(codebase, plan, _console)

    rel = str(file.relative_to(codebase))
    target_items = [
        item
        for session in plan["sessions"]
        for item in session["items"]
        if item["file"] == rel
    ]

    if not target_items:
        _console.print(f"[yellow]No items found for {rel} in the plan.[/yellow]")
        raise typer.Exit(0)

    if not _ensure_ollama_running(_console):
        raise typer.Exit(1)

    backend = OllamaBackend()
    verifier = Verifier(backend, _console)
    codebase_str = str(codebase)
    for item_data in target_items:
        item = item_from_data(item_data)
        record = verifier.run_lesson(item, codebase_str)
        append_session_record(codebase, record)


if __name__ == "__main__":
    sys.exit(app())

"""CLI entry point for code_tutor.

Commands:
    analyze  -- walk a codebase and produce a study plan
    study    -- run (or resume) an interactive study session
    status   -- show progress dashboard
    drill    -- force a lesson on a specific file
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time
from typing import cast

import requests
from rich.console import Console
from rich.table import Table
import typer

from python_pkg.code_tutor._analyzer import codebase_fingerprint, extract_items
from python_pkg.code_tutor._llm import OllamaBackend
from python_pkg.code_tutor._plan_builder import build_plan
from python_pkg.code_tutor._progress import (
    PlanData,
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


def _ensure_ollama_running(console: Console) -> bool:
    """Start the Ollama systemd service if it is not already reachable.

    Tries ``systemctl start ollama`` and polls the API for up to
    ``_OLLAMA_START_TIMEOUT`` seconds.

    Args:
        console: Rich console for status messages.

    Returns:
        True when Ollama is reachable, False after timeout.
    """
    try:
        requests.get(_OLLAMA_API, timeout=2)
    except requests.exceptions.RequestException:
        pass
    else:
        return True

    console.print("[yellow]Ollama not running -- starting via systemctl...[/yellow]")
    try:
        subprocess.run(
            ["systemctl", "start", "ollama"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]systemctl start ollama failed: {exc.stderr.decode().strip()}[/red]"
        )
        return False

    deadline = time.monotonic() + _OLLAMA_START_TIMEOUT
    while time.monotonic() < deadline:
        try:
            requests.get(_OLLAMA_API, timeout=2)
        except requests.exceptions.RequestException:
            time.sleep(1)
        else:
            console.print("[green]Ollama is up.[/green]")
            return True

    console.print("[red]Ollama did not become ready in time.[/red]")
    return False


def _ensure_fresh_plan(codebase: Path, plan: PlanData, console: Console) -> PlanData:
    """Rebuild *plan* if the codebase source files have changed since it was created.

    Compares the plan's stored fingerprint against the current one.  When they
    differ, re-runs the full analyze pipeline, saves the new plan to disk, and
    returns it.  Plans without a stored fingerprint (created before this feature)
    are returned unchanged.

    Args:
        codebase: Root directory of the codebase.
        plan: Plan dict loaded from ``plan.json``.
        console: Rich console for status messages.

    Returns:
        The original plan when up-to-date, or a freshly built ``PlanData`` when
        the fingerprint has changed.
    """
    saved = plan.get("source_fingerprint", "")
    if not saved:
        return plan
    current = codebase_fingerprint(codebase)
    if current == saved:
        return plan

    console.print(
        "[yellow]Plan is stale -- source files changed.  Rebuilding...[/yellow]"
    )
    items = extract_items(codebase)
    if not items:
        console.print("[red]No extractable items found -- keeping existing plan.[/red]")
        return plan

    new_plan = build_plan(codebase, items)
    save_plan(codebase, new_plan)
    n = new_plan["total_items"]
    console.print(f"[green]Plan rebuilt: {n} items.[/green]")
    return cast("PlanData", new_plan)


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


def _find_codebase_for_file(file: Path) -> Path | None:
    """Search all saved plans and return the codebase that contains *file*.

    Args:
        file: Absolute path to the source file.

    Returns:
        The codebase ``Path`` whose plan contains *file*, or ``None``.
    """
    config_root = Path.home() / ".config" / "code_tutor"
    if not config_root.exists():
        return None
    for plan_file in sorted(config_root.glob("*/plan.json")):
        result = _check_plan_file(plan_file, file)
        if result is not None:
            return result
    return None


def _check_plan_file(plan_file: Path, file: Path) -> Path | None:
    """Return the codebase path from *plan_file* if it contains *file*, else None.

    Args:
        plan_file: Path to a ``plan.json`` file.
        file: Absolute path to look up.

    Returns:
        The codebase ``Path`` when *file* is relative to it, or ``None``.
    """
    try:
        data = json.loads(plan_file.read_text(encoding="utf-8"))
        codebase = Path(str(data.get("codebase_path", "")))
        file.relative_to(codebase)
    except (ValueError, KeyError, OSError):
        return None
    return codebase


if __name__ == "__main__":
    sys.exit(app())

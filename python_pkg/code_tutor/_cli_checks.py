"""Ollama readiness and plan-freshness checks for the CLI commands.

Split out of :mod:`python_pkg.code_tutor.cli` to keep it under the 250-line
cap. ``cli`` imports all three entry points back, because the command tests
patch them on ``cli``; ``requests``, ``subprocess`` and ``time`` travel here
with the code that calls them, and the Ollama tests patch them on this module.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time
from typing import TYPE_CHECKING, cast

import requests

from python_pkg.code_tutor._analyzer import extract_items
from python_pkg.code_tutor._deps import codebase_fingerprint
from python_pkg.code_tutor._plan_builder import build_plan
from python_pkg.code_tutor._progress import save_plan

if TYPE_CHECKING:
    from rich.console import Console

    from python_pkg.code_tutor._progress import PlanData

_OLLAMA_API = "http://localhost:11434/api/tags"
_OLLAMA_START_TIMEOUT = 30


def _ollama_reachable() -> bool:
    """Return True when the Ollama API answers.

    Keeping the probe in its own function is what lets the readiness poll below
    stay a plain loop with no try/except in its body.
    """
    try:
        requests.get(_OLLAMA_API, timeout=2)
    except requests.exceptions.RequestException:
        return False
    return True


def _start_ollama_service(console: Console) -> bool:
    """Run ``systemctl start ollama``. Returns False when the call fails.

    Args:
        console: Rich console for status messages.
    """
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        console.print("[red]systemctl not found.[/red]")
        return False
    try:
        subprocess.run(
            [systemctl, "start", "ollama"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]systemctl start ollama failed: {exc.stderr.decode().strip()}[/red]"
        )
        return False
    return True


def _ensure_ollama_running(console: Console) -> bool:
    """Start the Ollama systemd service if it is not already reachable.

    Tries ``systemctl start ollama`` and polls the API for up to
    ``_OLLAMA_START_TIMEOUT`` seconds.

    Args:
        console: Rich console for status messages.

    Returns:
        True when Ollama is reachable, False after timeout.
    """
    if _ollama_reachable():
        return True

    console.print("[yellow]Ollama not running -- starting via systemctl...[/yellow]")
    if not _start_ollama_service(console):
        return False

    deadline = time.monotonic() + _OLLAMA_START_TIMEOUT
    while time.monotonic() < deadline:
        if _ollama_reachable():
            console.print("[green]Ollama is up.[/green]")
            return True
        time.sleep(1)

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

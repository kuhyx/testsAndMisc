"""Run every card example in Node and compare with the stated result."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_pkg.js_anki.models import Entry

RUNNER = Path(__file__).with_name("runner.js")


class VerificationError(Exception):
    """Raised when a card example does not produce its stated result."""


def run_examples(
    entries: list[Entry], node: str | None = None, timeout: int = 60
) -> dict[str, dict[str, object]]:
    """Execute all examples in one Node process; map uid -> runner result."""
    node_bin = node or shutil.which("node")
    if not node_bin:
        msg = "node not found on PATH"
        raise VerificationError(msg)
    payload = json.dumps([{"id": e.uid, "code": e.example} for e in entries])
    proc = subprocess.run(
        [node_bin, str(RUNNER)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        msg = f"node runner failed: {proc.stderr.strip()}"
        raise VerificationError(msg)
    return {r["id"]: r for r in json.loads(proc.stdout)}


def verify(entries: list[Entry], node: str | None = None) -> None:
    """Raise VerificationError listing every example that disagrees."""
    results = run_examples(entries, node)
    problems: list[str] = []
    for entry in entries:
        res = results.get(entry.uid)
        if res is None or not res["ok"]:
            err = res["error"] if res else "no result"
            problems.append(f"{entry.uid}: error: {err}")
        elif res["value"] != entry.expected:
            problems.append(
                f"{entry.uid}: expected {entry.expected} got {res['value']}"
            )
    if problems:
        raise VerificationError("\n".join(problems))

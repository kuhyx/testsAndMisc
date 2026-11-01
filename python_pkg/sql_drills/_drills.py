"""Drill discovery: one folder per drill under ``fixtures/``.

Each folder holds ``DOCS-task.md`` (statement), ``schema.sql`` (tables and data)
and ``expected.txt`` (the exact judge output). Reference solutions are NOT
here; they live under ``tests/solutions`` so learning mode never shows them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DRILLS_DIR = Path(__file__).parent / "fixtures"
SAMPLE_ROWS = 5


class UnknownDrillError(KeyError):
    """Raised when a drill id or number prefix matches nothing."""


@dataclass(frozen=True)
class Drill:
    """A drill's id and the three files that define it."""

    id: str
    task: Path
    schema: Path
    expected: Path


def list_drills(root: Path = DRILLS_DIR) -> list[Drill]:
    """All drills under ``root``, sorted by id (the priority order)."""
    if not root.is_dir():
        return []
    return [
        Drill(d.name, d / "DOCS-task.md", d / "schema.sql", d / "expected.txt")
        for d in sorted(root.iterdir())
        if d.is_dir()
    ]


def get_drill(key: str, root: Path = DRILLS_DIR) -> Drill:
    """Find a drill by full id or by its leading number (``03``)."""
    for drill in list_drills(root):
        if key in (drill.id, drill.id.split("_", 1)[0]):
            return drill
    msg = f"unknown drill: {key}"
    raise UnknownDrillError(msg)


def title_of(drill: Drill) -> str:
    """The task's first heading, without the leading ``#``."""
    return drill.task.read_text().splitlines()[0].lstrip("# ")


def render_show(drill: Drill) -> str:
    """Task text, schema, and the first rows of the expected output."""
    rows = drill.expected.read_text().splitlines()
    sample = "\n".join(rows[:SAMPLE_ROWS])
    more = f"\n... ({len(rows)} rows in total)" if len(rows) > SAMPLE_ROWS else ""
    return (
        f"{drill.task.read_text().strip()}\n\n"
        f"## Schema\n\n{drill.schema.read_text().strip()}\n\n"
        f"## Expected output (sample)\n\n{sample}{more}\n"
    )

"""USD per completed todo note: per-note rows, window metrics and outputs.

``usd_per_note`` = lifetime linked USD of notes done or abandoned in the window
over the notes done in the window that have a linked session (lower is
better). ``note_linked_usd_share`` is the share of window spend linked to any
note: how far to trust the first number.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING

from python_pkg.token_audit import history, notes_collect, pricing
from python_pkg.token_audit.notes_backlog import TERMINAL

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from python_pkg.token_audit.model import Session
    from python_pkg.token_audit.notes_backlog import Note
    from python_pkg.token_audit.notes_cost import Spend
    from python_pkg.token_audit.notes_link import Link

JSON_NAME = "notes.json"
TOP = 15
TITLE_CHARS = 60


@dataclass(frozen=True)
class NoteRow:
    """One note with the spend of every session linked to it."""

    id: str
    title: str
    status: str
    priority: str
    done_at: float | None
    sessions: list[str]
    usd: float
    tokens: int


def backlog_path_for(home: Path) -> Path:
    """BACKLOG.md under a given home directory."""
    return home / "src" / "todo" / "BACKLOG.md"


def note_rows(
    notes: list[Note], links: Mapping[str, Link], spend: Mapping[str, Spend]
) -> list[NoteRow]:
    """Notes with >=1 linked session; a session's spend splits equally."""
    usd: dict[str, float] = {}
    toks: dict[str, float] = {}
    sessions: dict[str, list[str]] = {}
    for sid in sorted(links):
        share = len(links[sid].notes)
        cost = spend.get(sid)
        for note_id in links[sid].notes:
            sessions.setdefault(note_id, []).append(sid)
            usd[note_id] = usd.get(note_id, 0.0) + (cost.usd / share if cost else 0.0)
            toks[note_id] = toks.get(note_id, 0) + (cost.tokens / share if cost else 0)
    rows = [
        NoteRow(
            n.id,
            n.title,
            n.status,
            n.priority,
            n.done_at,
            sessions[n.id],
            round(usd[n.id], 4),
            round(toks[n.id]),
        )
        for n in notes
        if n.id in sessions
    ]
    return sorted(rows, key=lambda r: -r.usd)


def _in(stamp: float | None, window: tuple[float, float]) -> bool:
    return stamp is not None and window[0] <= stamp <= window[1]


def metrics(
    notes: list[Note],
    rows: list[NoteRow],
    window: tuple[float, float],
    window_usd: Mapping[str, float],
    linked: set[str],
) -> dict[str, float]:
    """The snapshot metrics; ``usd_per_note`` is absent when unmeasurable."""
    done = {n.id for n in notes if n.status == "done" and _in(n.done_at, window)}
    closed = {n.id for n in notes if n.status == "abandoned" and _in(n.done_at, window)}
    linked_done = [r for r in rows if r.id in done]
    spent = sum(r.usd for r in rows if r.id in done | closed)
    total = sum(window_usd.values())
    linked_usd = sum(v for k, v in window_usd.items() if k in linked)
    out: dict[str, float] = {
        "note_linked_usd_share": round(linked_usd / total, 4) if total else 0.0,
        "notes_done": len(done),
        "notes_done_linked": len(linked_done),
    }
    if linked_done:
        out = {"usd_per_note": round(spent / len(linked_done), 2)} | out
    return out


def _day(stamp: float | None) -> str:
    if not stamp:
        return "-"
    return datetime.fromtimestamp(stamp, tz=UTC).astimezone().strftime("%Y-%m-%d")


def _title(text: str) -> str:
    text = text.replace("|", "\\|")
    return text if len(text) <= TITLE_CHARS else text[: TITLE_CHARS - 1] + "…"


def render(
    rows: list[NoteRow], found: Mapping[str, float], rules: Mapping[str, int]
) -> list[str]:
    """The WEEKLY.md section: metrics, link sources, top closed notes by USD."""
    per_note = found.get("usd_per_note")
    lines = [
        "## Cost per todo note",
        "",
        f"- usd_per_note: {'n/a' if per_note is None else f'${per_note:,.2f}'}"
        " (lower is better)",
        f"- note_linked_usd_share: {found['note_linked_usd_share'] * 100:.1f}%",
        f"- notes_done: {found['notes_done']} "
        f"({found.get('notes_done_linked', 0)} with a linked session)",
        "- links by rule: "
        + " ".join(f"{k}={rules.get(k, 0)}" for k in ("a", "b", "c", "d")),
        "",
        "| note | status | done | sessions | USD | tokens |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {_title(r.title)} | {r.status} | {_day(r.done_at)} | "
        f"{len(r.sessions)} | ${r.usd:,.2f} | {r.tokens:,} |"
        for r in rows[:TOP]
    ]
    return lines


def write_json(rows: list[NoteRow], out: Path) -> Path:
    """Write every linked note for the dashboard."""
    out.mkdir(parents=True, exist_ok=True)
    path = out / JSON_NAME
    data = {"generated": time.time(), "notes": [asdict(r) for r in rows]}
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return path


def section(
    root: Path,
    book: pricing.PriceBook,
    sessions: Sequence[Session],
    window: tuple[float, float],
) -> tuple[dict[str, float], list[str], list[NoteRow]] | None:
    """Metrics, WEEKLY.md lines and rows for one audit window."""
    started = time.monotonic()
    found = notes_collect.collect(root, book, sessions, window[0])
    if found is None:
        return None
    rows = note_rows(found.notes, found.links, found.spend)
    spent = notes_collect.window_usd(sessions, book)
    got = metrics(found.notes, rows, window, spent, set(found.links))
    rules = " ".join(f"{k}={v}" for k, v in sorted(found.rules.items()))
    sys.stderr.write(
        f"notes: {len(found.links)} sessions linked ({rules}) "
        f"in {time.monotonic() - started:.2f}s\n"
    )
    closed = [r for r in rows if r.status in TERMINAL and _in(r.done_at, window)]
    return got, ["", *render(closed, got, found.rules)], rows


def main(argv: list[str] | None = None) -> int:
    """Rewrite notes.json from all transcripts, independent of any window."""
    parser = argparse.ArgumentParser(prog="token_audit.notes")
    parser.add_argument("--root", type=Path, default=notes_collect.TRANSCRIPTS)
    parser.add_argument("--out", type=Path, default=history.REPORT_DIR)
    args = parser.parse_args(argv)
    found = notes_collect.collect(args.root, pricing.load(), [], float("inf"))
    if found is not None:
        written = write_json(note_rows(found.notes, found.links, found.spend), args.out)
        sys.stderr.write(f"Wrote {written}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

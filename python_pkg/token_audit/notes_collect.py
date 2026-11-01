"""Gather notes, session links and linked spend for the notes report."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from python_pkg.token_audit import notes_backlog, notes_cost, notes_link, notes_scan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_pkg.token_audit.model import Session
    from python_pkg.token_audit.notes_backlog import Note
    from python_pkg.token_audit.notes_cost import Spend
    from python_pkg.token_audit.notes_link import Link
    from python_pkg.token_audit.pricing import PriceBook

TRANSCRIPTS = Path.home() / ".claude" / "projects"


@dataclass(frozen=True)
class Collected:
    """Everything the notes metrics are computed from."""

    notes: list[Note]
    links: dict[str, Link]
    spend: dict[str, Spend]

    @property
    def rules(self) -> Counter[str]:
        """How many sessions each rule linked."""
        return Counter(link.rule for link in self.links.values())


def _reusable(
    sessions: Sequence[Session],
    facts: dict[str, notes_scan.Facts],
    since: float,
    book: PriceBook,
) -> dict[str, Spend]:
    out: dict[str, Spend] = {}
    for session in sessions:
        fact = facts.get(session.parent_id or session.session_id)
        if fact is not None and fact.start >= since:
            out[session.path] = notes_cost.of_session(session, book)
    return out


def collect(
    root: Path, book: PriceBook, sessions: Sequence[Session], since: float
) -> Collected | None:
    """Notes, links and lifetime spend; ``None`` when BACKLOG.md is missing."""
    backlog = notes_backlog.backlog_path()
    if not backlog.exists():
        sys.stderr.write(f"notes: skipped, no {backlog}\n")
        return None
    notes = notes_backlog.load_notes(backlog, notes_backlog.dumps_dir())
    facts = notes_scan.scan_root(root)
    links = notes_link.link_all(facts, notes)
    mains = {sid: fact.path for sid, fact in facts.items()}
    reuse = _reusable(sessions, facts, since, book)
    spend = notes_cost.lifetime(mains, set(links), book, reuse)
    return Collected(notes, links, spend)


def window_usd(sessions: Sequence[Session], book: PriceBook) -> dict[str, float]:
    """In-window USD per main session id, subagents folded into their parent."""
    out: dict[str, float] = {}
    for session in sessions:
        key = session.parent_id or session.session_id
        out[key] = out.get(key, 0.0) + notes_cost.of_session(session, book).usd
    return out

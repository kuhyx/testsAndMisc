"""Lifetime USD and tokens of the sessions linked to notes (main + subagents).

Window-free on purpose: a note finished this week was often worked last week.
Files already loaded whole by the audit are reused instead of re-parsed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from python_pkg.token_audit import parse, pricing
from python_pkg.token_audit.model import TOKEN_KINDS

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.token_audit.model import Session
    from python_pkg.token_audit.pricing import PriceBook


@dataclass(frozen=True)
class Spend:
    """Dollars at list price and raw tokens (all four classes)."""

    usd: float = 0.0
    tokens: int = 0

    def __add__(self, other: Spend) -> Spend:
        """Sum two spends."""
        return Spend(self.usd + other.usd, self.tokens + other.tokens)


def of_session(session: Session, book: PriceBook) -> Spend:
    """Spend of every turn a loaded session holds."""
    return Spend(
        sum(pricing.usd(turn, book) for turn in session.turns),
        sum(turn.usage.get(kind, 0) for turn in session.turns for kind in TOKEN_KINDS),
    )


def files_of(main: Path) -> list[Path]:
    """A main transcript plus every subagent transcript filed under it."""
    return [main, *sorted(main.with_suffix("").glob("subagents/agent-*.jsonl"))]


def lifetime(
    mains: dict[str, Path],
    wanted: set[str],
    book: PriceBook,
    reuse: dict[str, Spend],
) -> dict[str, Spend]:
    """Whole-file spend per wanted session id, reusing ``reuse[path]`` hits."""
    out: dict[str, Spend] = {}
    for sid in sorted(wanted & mains.keys()):
        total = Spend()
        for path in files_of(mains[sid]):
            hit = reuse.get(str(path))
            total += (
                hit if hit is not None else of_session(parse.load_session(path), book)
            )
        out[sid] = total
    return out

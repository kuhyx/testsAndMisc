"""Decide, on each timer tick, which style each monitor shows and whether to paint.

A new style comes every three hours, never the one that monitor just had and
never the one the other monitor shows. Between rotations the data-driven
styles redraw so their content stays current, and everything repaints when
the root pixmap is gone (new X session, or something else set a background).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path
    import random

ROTATE_EVERY = timedelta(hours=3)
# Styles whose picture depends on the time or on ledgers, not just the seed.
LIVE_STYLES = frozenset({"clock", "earth", "heatmap"})


@dataclass(frozen=True)
class Pick:
    """One monitor's style and the seed that makes its picture reproducible."""

    style: str
    seed: int


@dataclass(frozen=True)
class State:
    """What is on screen, since when, and which root pixmap carries it."""

    rotated_at: datetime
    picks: dict[str, Pick] = field(default_factory=dict)
    root_id: str | None = None

    def save(self, path: Path) -> None:
        """Write the state as JSON, creating the parent directory."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "rotated_at": self.rotated_at.isoformat(),
            "picks": {o: [p.style, p.seed] for o, p in self.picks.items()},
            "root_id": self.root_id,
        }
        path.write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> State | None:
        """Read a saved state; ``None`` when missing or unreadable."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            picks = {o: Pick(str(s), int(n)) for o, (s, n) in data["picks"].items()}
            return cls(
                datetime.fromisoformat(data["rotated_at"]), picks, data["root_id"]
            )
        except OSError, ValueError, KeyError, TypeError, AttributeError:
            return None


def choose(
    previous: Mapping[str, str],
    outputs: Sequence[str],
    names: Sequence[str],
    rng: random.Random,
) -> dict[str, str]:
    """Pick a style per output, unlike its previous one and unlike each other."""
    picked: dict[str, str] = {}
    for output in outputs:
        taken = {previous.get(output), *picked.values()}
        options = [n for n in names if n not in taken] or list(names)
        picked[output] = rng.choice(options)
    return picked


def plan(
    state: State | None,
    outputs: Sequence[str],
    now: datetime,
    names: Sequence[str],
    rng: random.Random,
    *,
    root_id: str | None,
) -> tuple[State, bool]:
    """Return the state to show and whether the root needs painting.

    Args:
        state: The saved state, or ``None`` on the first run.
        outputs: Active output names.
        now: Current time.
        names: Styles available right now.
        rng: Randomness for styles and seeds.
        root_id: The root pixmap id now on the X server, if any.
    """
    due = state is None or now - state.rotated_at >= ROTATE_EVERY
    if state is None or due:
        previous = {o: p.style for o, p in state.picks.items()} if state else {}
        styles = choose(previous, outputs, names, rng)
        picks = {o: Pick(s, rng.getrandbits(32)) for o, s in styles.items()}
        return State(now, picks, state.root_id if state else None), True
    missing = [o for o in outputs if o not in state.picks]
    if missing:
        others = {o: p.style for o, p in state.picks.items()}
        styles = choose(
            {}, missing, [n for n in names if n not in others.values()] or names, rng
        )
        picks = {
            **state.picks,
            **{o: Pick(s, rng.getrandbits(32)) for o, s in styles.items()},
        }
        return replace(state, picks=picks), True
    lost = root_id is None or root_id != state.root_id
    live = any(state.picks[o].style in LIVE_STYLES for o in outputs)
    return state, lost or live

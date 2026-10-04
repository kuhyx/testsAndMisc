"""Price turns in US dollars, per model.

The token-class weights in :mod:`model` are model-blind: an Opus call and a
Haiku call with identical usage weigh the same, so the weighted total cannot
say what moving work to a cheaper model would save. Dollars can. They are API
list prices -- on a subscription they are not what is billed, but they are the
best available proxy for how fast a usage limit drains, and they make Opus,
Sonnet and Haiku spend comparable.

One measured surprise this exposed: Sonnet 5.5 cache reads cost the same
$0.20/MTok as Opus 5.5. Cache reads are most of the bill, so moving a long
agent to Sonnet saves far less than the 2x the headline prices suggest.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.token_audit.records import CACHE_1H, CACHE_5M

if TYPE_CHECKING:
    from python_pkg.token_audit.model import Turn

PRICES_PATH = Path(__file__).with_name("prices.json")
PER_MILLION = 1_000_000
WRITE_5M = 1.25
WRITE_1H = 2.0


@dataclass(frozen=True)
class Price:
    """List prices for one model, USD per million tokens."""

    input: float
    output: float
    cache_read: float


@dataclass(frozen=True)
class PriceBook:
    """Every known model's price plus the fallback for unknown ids."""

    models: dict[str, Price]
    default: str

    def for_model(self, model: str) -> Price:
        """Exact id, else the longest known id it starts with, else default.

        The prefix match covers dated or suffixed ids (``claude-haiku-4-5-2025...``).
        """
        if model in self.models:
            return self.models[model]
        matches = [known for known in self.models if model.startswith(known)]
        if matches:
            return self.models[max(matches, key=len)]
        return self.models[self.default]


def load(path: Path = PRICES_PATH) -> PriceBook:
    """Read the price table shipped next to this module."""
    data = json.loads(path.read_text(encoding="utf-8"))
    models = {
        name: Price(
            input=float(row["input"]),
            output=float(row["output"]),
            cache_read=float(row["cache_read"]),
        )
        for name, row in data["models"].items()
    }
    return PriceBook(models=models, default=str(data["default"]))


def usd(turn: Turn, book: PriceBook) -> float:
    """Return one turn's list-price cost in dollars.

    Synthetic turns (``<synthetic>``) carry zero usage and so cost zero under
    any price, which is why no special case is needed for them. When a turn
    has no 1h/5m split, the whole cache write is priced as 5m (the cheaper,
    older default) -- an underestimate, never an overestimate.
    """
    usage = turn.usage
    price = book.for_model(turn.model)
    creation = usage.get("cache_creation_input_tokens", 0)
    one_hour = usage.get(CACHE_1H, 0)
    five_min = usage.get(CACHE_5M, creation - one_hour)
    total = (
        usage.get("input_tokens", 0) * price.input
        + five_min * WRITE_5M * price.input
        + one_hour * WRITE_1H * price.input
        + usage.get("cache_read_input_tokens", 0) * price.cache_read
        + usage.get("output_tokens", 0) * price.output
    )
    return total / PER_MILLION

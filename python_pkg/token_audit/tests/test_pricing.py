from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_pkg.token_audit import pricing
from python_pkg.token_audit.model import Turn

BOOK = pricing.PriceBook(
    models={
        "claude-opus-5": pricing.Price(input=5.0, output=25.0, cache_read=0.5),
        "claude-opus-5-5": pricing.Price(input=4.0, output=20.0, cache_read=0.2),
    },
    default="claude-opus-5",
)


def _turn(usage: dict[str, int], model: str = "claude-opus-5") -> Turn:
    return Turn(usage=usage, context=0, model=model, is_sidechain=False)


def test_for_model_exact_prefix_and_default() -> None:
    assert BOOK.for_model("claude-opus-5").input == 5.0
    # Longest matching known id wins over a shorter prefix.
    assert BOOK.for_model("claude-opus-5-5-2026").input == 4.0
    assert BOOK.for_model("mystery").input == 5.0


def test_load_reads_shipped_table() -> None:
    book = pricing.load()
    assert book.default in book.models
    assert book.for_model("claude-sonnet-5-5").cache_read == 0.2


def test_load_custom_path(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    path.write_text(
        json.dumps(
            {
                "default": "m",
                "models": {"m": {"input": 1, "output": 2, "cache_read": 3}},
            },
        ),
        encoding="utf-8",
    )
    book = pricing.load(path)
    assert book.models["m"] == pricing.Price(1.0, 2.0, 3.0)


def test_usd_without_split_prices_creation_as_5m() -> None:
    usage = {"input_tokens": 1_000_000, "cache_creation_input_tokens": 1_000_000}
    assert pricing.usd(_turn(usage), BOOK) == pytest.approx(5.0 + 1.25 * 5.0)


def test_usd_with_split_prices_1h_at_double() -> None:
    usage = {
        "cache_creation_input_tokens": 1_000_000,
        "cache_creation_1h": 400_000,
        "cache_creation_5m": 600_000,
        "cache_read_input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
    }
    expected = 0.4 * 2.0 * 5.0 + 0.6 * 1.25 * 5.0 + 0.5 + 25.0
    assert pricing.usd(_turn(usage), BOOK) == pytest.approx(expected)


def test_usd_zero_for_empty_usage() -> None:
    assert pricing.usd(_turn({}), BOOK) == 0.0

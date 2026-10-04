"""Turn verified entries into a genanki package (flip + self-grade cards)."""

from __future__ import annotations

import hashlib
from html import escape
from typing import TYPE_CHECKING

import genanki

if TYPE_CHECKING:
    from python_pkg.js_anki.models import Entry

_ID_SPACE = 1 << 31
CSS = """
.card { font-family: system-ui, sans-serif; font-size: 20px; text-align: left;
  color: #e6e6e6; background: #1b1d21; padding: 12px; }
pre { background: #25282e; padding: 10px; border-radius: 6px;
  overflow-x: auto; white-space: pre-wrap; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 17px; }
.gotcha { color: #f0b429; margin-top: 10px; }
.res { color: #7bd88f; }
"""


def stable_id(key: str) -> int:
    """Deterministic 31-bit id so re-imports update instead of duplicating."""
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % _ID_SPACE


def build_model() -> genanki.Model:
    """The single two-field note type shared by all cards."""
    return genanki.Model(
        stable_id("js_anki:model:v1"),
        "JS method (js_anki)",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": "Card",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
            }
        ],
        css=CSS,
    )


def deck_name(entry: Entry) -> str:
    """Subdeck for an entry: JS::Array, JS::Array::Rare, JS::Extras, ..."""
    base = f"JS::{entry.family.capitalize()}"
    if entry.family != "extras" and entry.tier == "rare":
        return f"{base}::Rare"
    return base


def _code(text: str) -> str:
    return f"<pre><code>{escape(text)}</code></pre>"


def _gotcha(entry: Entry) -> str:
    return f'<div class="gotcha">⚠ {escape(entry.gotcha)}</div>' if entry.gotcha else ""


def cards_for(entry: Entry) -> list[tuple[str, str, str]]:
    """Return (kind, front, back) triples for one entry."""
    name = f"<code>{escape(entry.method)}</code>"
    task_back = (
        f"{_code(entry.call)}{_code(entry.example)}"
        f'<div class="res">→ {escape(entry.expected)}</div>{_gotcha(entry)}'
    )
    cards = [("task", escape(entry.task), task_back)]
    if entry.mutates is not None:
        mut = (
            "Yes — mutates the original" if entry.mutates else "No — original untouched"
        )
        cards.append(
            (
                "behaviour",
                f"{name}: does it mutate the original, and what does it return?",
                f"<b>{mut}</b><br>Returns: {escape(entry.returns)}{_gotcha(entry)}",
            )
        )
    if entry.signature:
        cards.append(
            ("args", f"{name}: argument order / signature?", _code(entry.signature))
        )
    return cards


def build_package(entries: list[Entry]) -> tuple[genanki.Package, int]:
    """Build the .apkg package; returns (package, card_count)."""
    model = build_model()
    decks: dict[str, genanki.Deck] = {}
    count = 0
    for entry in entries:
        name = deck_name(entry)
        deck = decks.setdefault(name, genanki.Deck(stable_id(f"deck:{name}"), name))
        for kind, front, back in cards_for(entry):
            deck.add_note(
                genanki.Note(
                    model=model,
                    fields=[front, back],
                    tags=[entry.family, entry.tier],
                    guid=genanki.guid_for("js_anki", entry.uid, kind),
                )
            )
            count += 1
    return genanki.Package(list(decks.values())), count

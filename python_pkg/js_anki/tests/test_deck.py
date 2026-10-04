"""Tests for python_pkg.js_anki.deck."""

from __future__ import annotations

import dataclasses

from python_pkg.js_anki.deck import (
    build_package,
    cards_for,
    deck_name,
    stable_id,
)
from python_pkg.js_anki.models import Entry

BASE = Entry(
    family="array",
    method="m<b>",
    tier="core",
    task="do <it>",
    call="a.m()",
    returns="thing",
    example="return 1;",
    expected="1",
)


def test_stable_id_deterministic() -> None:
    assert stable_id("x") == stable_id("x") != stable_id("y")


def test_deck_names() -> None:
    assert deck_name(BASE) == "JS::Array"
    assert deck_name(dataclasses.replace(BASE, tier="rare")) == "JS::Array::Rare"
    assert (
        deck_name(dataclasses.replace(BASE, family="extras", tier="rare"))
        == "JS::Extras"
    )


def test_task_card_only_and_escaping() -> None:
    cards = cards_for(BASE)
    assert [k for k, _, _ in cards] == ["task"]
    assert "do &lt;it&gt;" in cards[0][1]
    assert "gotcha" not in cards[0][2]


def test_behaviour_card_mutating_and_pure() -> None:
    mut = cards_for(dataclasses.replace(BASE, mutates=True, gotcha="careful"))
    assert [k for k, _, _ in mut] == ["task", "behaviour"]
    assert "Yes" in mut[1][2]
    assert "careful" in mut[1][2]
    pure = cards_for(dataclasses.replace(BASE, mutates=False))
    assert "No" in pure[1][2]


def test_args_card() -> None:
    cards = cards_for(dataclasses.replace(BASE, signature="m(a, b)"))
    assert [k for k, _, _ in cards] == ["task", "args"]
    assert "m(a, b)" in cards[1][2]


def test_build_package_counts_and_groups() -> None:
    rare = dataclasses.replace(BASE, method="r", tier="rare", mutates=True)
    package, count = build_package([BASE, rare])
    assert count == 3
    assert sorted(d.name for d in package.decks) == ["JS::Array", "JS::Array::Rare"]

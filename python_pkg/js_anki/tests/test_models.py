"""Tests for python_pkg.js_anki.models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_pkg.js_anki.models import FAMILIES, load_all, load_family, parse_entry

RAW = {
    "method": "push",
    "tier": "core",
    "task": "t",
    "call": "c",
    "returns": "r",
    "example": "return 1;",
    "expected": "1",
}


def test_parse_entry_defaults() -> None:
    entry = parse_entry("array", RAW)
    assert entry.uid == "array:push"
    assert entry.mutates is None
    assert not entry.signature
    assert not entry.gotcha


def test_parse_entry_optional_fields() -> None:
    entry = parse_entry(
        "array", {**RAW, "mutates": True, "signature": "s", "gotcha": "g"}
    )
    assert (entry.mutates, entry.signature, entry.gotcha) == (True, "s", "g")


def test_missing_required_key() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_entry("array", {k: v for k, v in RAW.items() if k != "call"})


def test_bad_tier() -> None:
    with pytest.raises(ValueError, match="tier"):
        parse_entry("array", {**RAW, "tier": "hard"})


def test_unknown_key() -> None:
    with pytest.raises(ValueError, match="unknown keys"):
        parse_entry("array", {**RAW, "typo": 1})


def test_load_family_reads_json(tmp_path: Path) -> None:
    (tmp_path / "array.json").write_text(json.dumps([RAW]), encoding="utf-8")
    assert [e.method for e in load_family("array", tmp_path)] == ["push"]


def test_load_all_rejects_duplicates(tmp_path: Path) -> None:
    for fam in FAMILIES:
        data = [RAW, RAW] if fam == "array" else []
        (tmp_path / f"{fam}.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_all(tmp_path)


def test_shipped_data_loads() -> None:
    entries = load_all()
    assert len(entries) > 90

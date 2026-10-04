"""Typed card-entry model and JSON loader for the JS-method data files."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent
FAMILIES = ("array", "string", "extras")
TIERS = frozenset({"core", "rare"})
_REQUIRED = ("method", "tier", "task", "call", "returns", "example", "expected")


@dataclass(frozen=True)
class Entry:
    """One method/idiom and everything the cards are generated from.

    `example` is a JS function body ending in `return`; `expected` is the exact
    `JSON.stringify` of that return value (or `undefined`).
    """

    family: str
    method: str
    tier: str
    task: str
    call: str
    returns: str
    example: str
    expected: str
    mutates: bool | None = None
    signature: str = ""
    gotcha: str = ""

    @property
    def uid(self) -> str:
        """Stable identity used for GUIDs and verification ids."""
        return f"{self.family}:{self.method}"


def parse_entry(family: str, raw: dict[str, Any]) -> Entry:
    """Validate one raw JSON object and build an Entry."""
    missing = [k for k in _REQUIRED if not raw.get(k)]
    if missing:
        msg = f"{family}: entry {raw.get('method', '?')!r} missing {missing}"
        raise ValueError(msg)
    if raw["tier"] not in TIERS:
        msg = f"{family}:{raw['method']}: tier must be one of {sorted(TIERS)}"
        raise ValueError(msg)
    unknown = set(raw) - set(_REQUIRED) - {"mutates", "signature", "gotcha"}
    if unknown:
        msg = f"{family}:{raw['method']}: unknown keys {sorted(unknown)}"
        raise ValueError(msg)
    return Entry(
        family=family,
        **{k: raw[k] for k in _REQUIRED},
        mutates=raw.get("mutates"),
        signature=raw.get("signature", ""),
        gotcha=raw.get("gotcha", ""),
    )


def load_family(family: str, data_dir: Path = DATA_DIR) -> list[Entry]:
    """Load and validate `<family>.json`."""
    raw = json.loads((data_dir / f"{family}.json").read_text(encoding="utf-8"))
    return [parse_entry(family, item) for item in raw]


def load_all(data_dir: Path = DATA_DIR) -> list[Entry]:
    """Load every family; reject duplicate identities."""
    entries = [e for fam in FAMILIES for e in load_family(fam, data_dir)]
    seen: set[str] = set()
    for entry in entries:
        if entry.uid in seen:
            msg = f"duplicate entry {entry.uid}"
            raise ValueError(msg)
        seen.add(entry.uid)
    return entries

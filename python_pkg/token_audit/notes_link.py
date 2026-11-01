"""Link sessions to todo notes; the first rule that yields a note decides.

a: a Bash call ran ``note_claim.sh <id>``; b: a typed prompt names
``todo-images/<uuid>/``; c: the first prompt fuzzy-matches one note;
d: an ``Implement|Continue <handoff>`` session inherits its writer's notes.
"""

from __future__ import annotations

from dataclasses import dataclass
import functools
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from python_pkg.token_audit.notes_backlog import Note
    from python_pkg.token_audit.notes_scan import Facts

FUZZY_THRESHOLD = 0.5
MIN_TOKENS = 4
MAX_IMAGE_NOTES = 2
_TOKEN = re.compile(r"[^\W_]{3,}")
_STOP = frozenset(
    [
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "you",
        "are",
        "not",
        "but",
        "have",
        "from",
        "what",
        "when",
        "where",
        "should",
        "would",
        "can",
        "will",
        "just",
        "all",
        "any",
        "its",
        "into",
        "also",
        "then",
        "than",
        "them",
        "they",
        "their",
        "there",
        "was",
        "were",
        "been",
        "being",
        "lets",
        "let",
        "make",
        "made",
        "does",
        "dont",
    ]
)


@dataclass(frozen=True)
class Link:
    """The notes one session worked on and the rule that found them."""

    notes: tuple[str, ...]
    rule: str


@functools.cache
def tokens(text: str) -> frozenset[str]:
    """Normalised content words: lower-case, 3+ letters, no stopwords/digits."""
    return frozenset(
        t for t in _TOKEN.findall(text.lower()) if t not in _STOP and not t.isdigit()
    )


def _dice(left: frozenset[str], right: frozenset[str]) -> float:
    total = len(left) + len(right)
    return 2 * len(left & right) / total if total else 0.0


def score(prompt: str, note: Note) -> float:
    """Body overlap, or the prompt's first line against the note title."""
    body = _dice(tokens(prompt), tokens(note.body))
    title = tokens(note.title)
    if len(title) < MIN_TOKENS:
        return body
    first_line = prompt.strip().splitlines()[0] if prompt.strip() else ""
    return max(body, _dice(tokens(first_line), title))


def resolve(token: str, ids: Iterable[str]) -> str | None:
    """The one note id ``token`` names (full id or unique prefix)."""
    token = token.lower()
    found = [i for i in ids if i.lower().startswith(token)]
    return found[0] if len(found) == 1 else None


def _explicit(facts: Facts, ids: list[str]) -> tuple[str, ...]:
    found = (resolve(token, ids) for token in facts.claims)
    return tuple(dict.fromkeys(i for i in found if i is not None))


def _images(facts: Facts, ids: set[str]) -> tuple[str, ...]:
    known = tuple(i for i in facts.images if i in ids)
    return known if len(known) <= MAX_IMAGE_NOTES else ()


def _fuzzy(facts: Facts, notes: list[Note]) -> tuple[str, ...]:
    if facts.handoff or len(tokens(facts.first_prompt)) < MIN_TOKENS:
        return ()
    scored = [(score(facts.first_prompt, n), n.updated or 0.0, n.id) for n in notes]
    best = max(scored, default=(0.0, 0.0, ""))
    return (best[2],) if best[0] >= FUZZY_THRESHOLD else ()


def _writers(facts: dict[str, Facts]) -> dict[str, tuple[float, str]]:
    first: dict[str, tuple[float, str]] = {}
    for sid, fact in facts.items():
        for rel, stamp in fact.creates.items():
            first[rel] = min(first.get(rel, (stamp, sid)), (stamp, sid))
    return first


def link_all(facts: dict[str, Facts], notes: list[Note]) -> dict[str, Link]:
    """Links per session id, resolved in start order so writers come first."""
    ids = [n.id for n in notes if n.id]
    writers = _writers(facts)
    links: dict[str, Link] = {}
    for sid in sorted(facts, key=lambda s: (facts[s].start, s)):
        fact = facts[sid]
        for rule, found in (
            ("a", _explicit(fact, ids)),
            ("b", _images(fact, set(ids))),
            ("c", _fuzzy(fact, notes)),
        ):
            if found:
                links[sid] = Link(found, rule)
                break
        else:
            writer = writers.get(fact.handoff or "")
            if writer and writer[1] != sid and writer[0] <= fact.start:
                inherited = links.get(writer[1])
                if inherited is not None:
                    links[sid] = Link(inherited.notes, "d")
    return links

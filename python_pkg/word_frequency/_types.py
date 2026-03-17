"""Shared types and constants for the Anki generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

_MIN_VOCAB_DUMP_PARTS = 2
_MIN_EXCERPT_PARTS = 3
_ONE_KB = 1024
_ONE_MB = 1024 * 1024


@dataclass(frozen=True)
class FlashcardOptions:
    """Options for flashcard generation."""

    source_lang: str | None = None
    target_lang: str = "en"
    deck_name: str | None = None
    include_context: bool = False
    no_translate: bool = False
    force: bool = False


@dataclass(frozen=True)
class DeckInput:
    """Input data for Anki deck generation."""

    words_with_ranks: list[tuple[str, int]]
    source_lang: str
    target_lang: str = "en"
    contexts: dict[str, str] | None = None
    deck_name: str = "Vocabulary"


# Path to C vocabulary_curve executable
C_EXECUTABLE = (
    Path(__file__).parent.parent.parent / "C" / "vocabulary_curve" / "vocabulary_curve"
)


class VocabWord(NamedTuple):
    """A vocabulary word with its metadata."""

    word: str
    rank: int
    translation: str
    context: str

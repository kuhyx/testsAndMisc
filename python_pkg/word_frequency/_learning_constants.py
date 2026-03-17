"""Constants and configuration for the learning pipe module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Common stopwords for various languages (can be overridden with --stopwords)
DEFAULT_STOPWORDS_EN = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "as",
        "if",
        "then",
        "because",
        "while",
        "although",
        "though",
        "after",
        "before",
    }
)


def load_stopwords(filepath: str | Path | None) -> frozenset[str]:
    """Load stopwords from a file (one word per line).

    Args:
        filepath: Path to stopwords file, or None to use defaults.

    Returns:
        Frozenset of stopwords.
    """
    if filepath is None:
        return frozenset()

    path = Path(filepath)
    if not path.exists():
        return frozenset()

    content = path.read_text(encoding="utf-8")
    return frozenset(
        word.strip().lower() for word in content.splitlines() if word.strip()
    )


@dataclass(frozen=True)
class LessonConfig:
    """Configuration for learning lesson generation."""

    batch_size: int = 20
    num_batches: int = 1
    excerpt_length: int = 30
    excerpts_per_batch: int = 3
    stopwords: frozenset[str] | None = None
    skip_default_stopwords: bool = False
    skip_numbers: bool = True
    case_sensitive: bool = False
    translate_from: str | None = None
    translate_to: str | None = None


def _resolve_stopwords(config: LessonConfig) -> frozenset[str]:
    """Resolve combined stopwords from config."""
    if config.skip_default_stopwords:
        return config.stopwords or frozenset()
    return DEFAULT_STOPWORDS_EN | (config.stopwords or frozenset())

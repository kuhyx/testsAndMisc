"""Dictionary loading for the keyboard cooperative word game."""

from __future__ import annotations

import json
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

_FALLBACK_DICTIONARY = {
    "cat",
    "dog",
    "car",
    "bat",
    "rat",
    "hat",
    "mat",
    "sat",
    "fat",
    "pat",
    "the",
    "and",
    "for",
    "are",
    "but",
    "not",
    "you",
    "all",
    "can",
    "had",
    "her",
    "was",
    "one",
    "our",
    "out",
    "day",
    "get",
    "has",
    "him",
    "his",
    "how",
    "man",
    "new",
    "now",
    "old",
    "see",
    "two",
    "way",
    "who",
    "boy",
    "work",
    "know",
    "place",
    "year",
    "live",
    "me",
    "back",
    "give",
    "good",
}


def load_dictionary(dictionary_dir: Path) -> set[str]:
    """Load dictionary from words_dictionary.json file.

    Args:
        dictionary_dir: Directory containing words_dictionary.json.

    Returns:
        Set of valid English words.
    """
    try:
        dictionary_path = dictionary_dir / "words_dictionary.json"
        with dictionary_path.open(encoding="utf-8") as f:
            dictionary_data = json.load(f)
        # Convert to set for faster lookup (we only need the keys)
        return set(dictionary_data.keys())
    except FileNotFoundError:
        _logger.warning(
            "words_dictionary.json not found, using fallback dictionary"
        )
        return set(_FALLBACK_DICTIONARY)
    except json.JSONDecodeError:
        _logger.warning(
            "Error reading words_dictionary.json, using fallback dictionary"
        )
        return set(_FALLBACK_DICTIONARY)

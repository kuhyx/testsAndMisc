"""Parsing functions for vocabulary curve output."""

from __future__ import annotations

import contextlib
import re

from python_pkg.word_frequency._types import (
    _MIN_EXCERPT_PARTS,
    _MIN_VOCAB_DUMP_PARTS,
)


def _parse_vocab_dump(lines: list[str]) -> list[tuple[str, int]]:
    """Parse VOCAB_DUMP section from output lines.

    Args:
        lines: Output lines from vocabulary_curve.

    Returns:
        List of (word, rank) tuples.
    """
    all_vocab: list[tuple[str, int]] = []
    in_vocab_dump = False
    for line in lines:
        stripped = line.strip()
        if stripped == "VOCAB_DUMP_START":
            in_vocab_dump = True
            continue
        if stripped == "VOCAB_DUMP_END":
            break
        if in_vocab_dump and ";" in stripped:
            parts = stripped.split(";")
            if len(parts) == _MIN_VOCAB_DUMP_PARTS:
                word, rank_str = parts
                with contextlib.suppress(ValueError):
                    all_vocab.append((word, int(rank_str)))
    return all_vocab


def _parse_excerpt_lines(lines: list[str], start: int) -> str:
    """Parse excerpt text from output lines starting after 'Excerpt:'.

    Args:
        lines: Output lines.
        start: Index of the line after 'Excerpt:'.

    Returns:
        Joined excerpt text.
    """
    excerpt_parts: list[str] = []
    idx = start
    while idx < len(lines):
        next_line = lines[idx].strip()
        next_line = next_line.removeprefix('"')
        if next_line.endswith('"'):
            next_line = next_line[:-1]
            excerpt_parts.append(next_line)
            break
        excerpt_parts.append(next_line)
        idx += 1
    return " ".join(excerpt_parts)


def parse_inverse_mode_output(
    output: str,
) -> tuple[str, int, int, list[tuple[str, int]]]:
    """Parse output from vocabulary_curve inverse mode.

    Args:
        output: Raw output from vocabulary_curve --max-vocab.

    Returns:
        Tuple of (excerpt_text, excerpt_length, max_rank_used, all_vocab_words).
    """
    lines = output.split("\n")
    excerpt = ""
    excerpt_length = 0
    max_rank_used = 0

    for i, raw_line in enumerate(lines):
        line = raw_line.strip()

        if line.startswith("LONGEST EXCERPT:"):
            parts = line.split()
            if len(parts) >= _MIN_EXCERPT_PARTS:
                excerpt_length = int(parts[2])

        elif line.startswith("Excerpt:"):
            excerpt = _parse_excerpt_lines(lines, i + 1)

        elif line.startswith("Rarest word used:"):
            match = re.search(r"\(#(\d+)\)", line)
            if match:
                max_rank_used = int(match.group(1))

    all_vocab = _parse_vocab_dump(lines)
    return excerpt, excerpt_length, max_rank_used, all_vocab


def _parse_target_length_block(
    lines: list[str],
    target_length: int,
) -> tuple[str, list[tuple[str, int]]]:
    """Parse the [Length N] block from vocabulary curve output.

    Args:
        lines: Output lines.
        target_length: Target excerpt length to find.

    Returns:
        Tuple of (excerpt, excerpt_words).
    """
    excerpt = ""
    excerpt_words: list[tuple[str, int]] = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith(f"[Length {target_length}]"):
            i += 1
            # Find excerpt line
            while i < len(lines) and not lines[i].strip().startswith("Excerpt:"):
                i += 1
            if i < len(lines):
                excerpt_line = lines[i].strip()
                if '"' in excerpt_line:
                    start = excerpt_line.index('"') + 1
                    end = excerpt_line.rindex('"')
                    excerpt = excerpt_line[start:end]
            # Find words line
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("Words:"):
                i += 1
            if i < len(lines):
                words_line = lines[i].strip()
                if words_line.startswith("Words:"):  # pragma: no branch
                    words_part = words_line[6:].strip()
                    pattern = r"(\S+)\(#(\d+)\)"
                    matches = re.findall(pattern, words_part)
                    excerpt_words = [(w, int(r)) for w, r in matches]
            break
        i += 1
    return excerpt, excerpt_words


def parse_vocabulary_curve_output(
    output: str, target_length: int
) -> tuple[str, list[tuple[str, int]], list[tuple[str, int]]]:
    """Parse output from vocabulary_curve to get words needed.

    Args:
        output: Raw output from vocabulary_curve.
        target_length: The target excerpt length.

    Returns:
        Tuple of (excerpt_text, excerpt_words, all_vocab_words).
        excerpt_words: words in the excerpt with their ranks.
        all_vocab_words: all words up to max rank
            (from VOCAB_DUMP if present).
    """
    lines = output.split("\n")

    excerpt, excerpt_words = _parse_target_length_block(lines, target_length)
    all_vocab = _parse_vocab_dump(lines)

    return excerpt, excerpt_words, all_vocab

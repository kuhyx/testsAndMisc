#!/usr/bin/env python3
"""Sherlock - simple text plagiarism detector using n-gram fingerprinting.

Extracted from `install_plagiarism_tools.sh`'s fallback path, which used to
write this out via a `cat <<'SHERLOCKEOF'` heredoc when cloning the real
sherlock-py failed. Inline heredoc Python is invisible to ruff, mypy, pylint,
bandit and pytest, so it lives in its own module instead, matching
`download_nltk_data.py`'s extraction.

The installer copies this file into `$SHERLOCK_DIR/sherlock.py` only when
`git clone` of the upstream tool fails.
"""

from __future__ import annotations

import argparse
import hashlib
from itertools import combinations
from pathlib import Path
import sys

#: Minimum number of input files for a pairwise comparison to make sense.
MIN_FILES = 2


def _out(line: str = "") -> None:
    sys.stdout.write(line + "\n")


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric words."""
    return [w.lower() for w in text.split() if w.isalnum()]


def get_ngrams(tokens: list[str], n: int = 3) -> list[tuple[str, ...]]:
    """Generate n-grams from a token list."""
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def fingerprint(text: str, ngram_size: int = 3, sample_rate: int = 4) -> set[str]:
    """Create a document fingerprint from sampled n-gram hashes."""
    tokens = tokenize(text)
    ngrams = get_ngrams(tokens, ngram_size)

    fingerprints = set()
    for i, ng in enumerate(ngrams):
        if i % sample_rate == 0:
            h = hashlib.md5("".join(ng).encode(), usedforsecurity=False).hexdigest()[:8]
            fingerprints.add(h)

    return fingerprints


def compare_documents(fp1: set[str], fp2: set[str]) -> float:
    """Jaccard similarity between two fingerprints."""
    if not fp1 or not fp2:
        return 0.0
    intersection = len(fp1 & fp2)
    union = len(fp1 | fp2)
    return intersection / union if union > 0 else 0.0


def read_document(filepath: str) -> str:
    """Read a document's raw text content."""
    with Path(filepath).open(encoding="utf-8", errors="ignore") as f:
        return f.read()


def main() -> int:
    """Fingerprint every input file and report pairwise similarity."""
    parser = argparse.ArgumentParser(description="Sherlock - Text Plagiarism Detector")
    parser.add_argument("files", nargs="+", help="Files to compare")
    parser.add_argument(
        "--ngram", "-n", type=int, default=3, help="N-gram size (default: 3)"
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=0.1, help="Similarity threshold"
    )

    args = parser.parse_args()

    if len(args.files) < MIN_FILES:
        _out("Need at least 2 files to compare")
        return 1

    docs = {}
    for f in args.files:
        if Path(f).exists():
            text = read_document(f)
            docs[f] = fingerprint(text, args.ngram)

    _out("\nSherlock Plagiarism Analysis")
    _out("=" * 50)

    files = list(docs.keys())
    for file1, file2 in combinations(files, 2):
        sim = compare_documents(docs[file1], docs[file2])
        name1 = Path(file1).name
        name2 = Path(file2).name
        flag = " ⚠️ SUSPICIOUS" if sim >= args.threshold else ""
        _out(f"{name1} <-> {name2}: {sim:.1%}{flag}")

    _out("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

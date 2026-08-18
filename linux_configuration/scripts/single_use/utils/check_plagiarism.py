#!/usr/bin/env python3
"""Compare documents for similarity using TF-IDF cosine similarity.

Extracted from `install_plagiarism_tools.sh`, which used to write this out via
a `cat <<'PYEOF'` heredoc. Inline heredoc Python is invisible to ruff, mypy,
pylint, bandit and pytest, so it lives in its own module instead, matching
`download_nltk_data.py`'s extraction. The comparison engine (file reading,
preprocessing, TF-IDF scoring) lives in `plagiarism_similarity.py`, split out
to keep both files under the 250-line cap.

The installer copies this file into `$INSTALL_DIR/check_plagiarism.py` and
wires the `plagcheck` wrapper to run it inside the venv.

Usage:
    python check_plagiarism.py file1.txt file2.txt [file3.txt ...]
    python check_plagiarism.py --dir /path/to/documents/
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from plagiarism_similarity import (
    compute_similarity_matrix,
    find_similar_passages,
    preprocess_text,
    read_file,
)

#: Minimum number of documents needed for a pairwise comparison to make sense.
MIN_DOCUMENTS = 2


def _out(line: str = "") -> None:
    sys.stdout.write(line + "\n")


def _collect_files(args: argparse.Namespace) -> list[str]:
    files: list[str] = list(args.files)
    if args.dir:
        dir_path = Path(args.dir)
        for ext in ("*.txt", "*.pdf", "*.docx", "*.md", "*.tex"):
            files.extend(str(f) for f in dir_path.glob(ext))
    return files


def _read_documents(files: list[str]) -> tuple[list[str], list[str]]:
    documents: list[str] = []
    filenames: list[str] = []
    for f in files:
        if not Path(f).exists():
            _out(f"Warning: {f} does not exist")
            continue
        text = read_file(f)
        if text.strip():
            documents.append(preprocess_text(text))
            filenames.append(Path(f).name)
        else:
            _out(f"Warning: {f} is empty or unreadable")
    return documents, filenames


def _report_pairs(
    documents: list[str],
    filenames: list[str],
    sim_matrix: list[list[float]],
    threshold: float,
) -> list[tuple[int, int, float, str]]:
    _out(f"{'Document Pair':<50} {'Similarity':>12}")
    _out("-" * 62)

    suspicious_pairs: list[tuple[int, int, float, str]] = []
    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            similarity = sim_matrix[i][j]
            pair_name = f"{filenames[i]} <-> {filenames[j]}"
            if similarity >= threshold:
                suspicious_pairs.append((i, j, similarity, pair_name))
                _out(f"{pair_name:<50} {similarity:>10.1%} ⚠️")
            else:
                _out(f"{pair_name:<50} {similarity:>10.1%}")

    _out("-" * 62)
    return suspicious_pairs


def _print_detailed_passages(
    files: list[str], suspicious_pairs: list[tuple[int, int, float, str]]
) -> None:
    _out("\n" + "=" * 60)
    _out(" Detailed Similar Passages")
    _out("=" * 60)

    for i, j, sim, pair_name in suspicious_pairs[:3]:
        _out(f"\n{pair_name} ({sim:.1%} similar):")
        _out("-" * 40)

        raw_docs = [read_file(files[i]), read_file(files[j])]
        passages = find_similar_passages(raw_docs[0], raw_docs[1])

        for s1, s2, psim in passages[:5]:
            _out(f'\n[{psim:.0%}] Document 1: "{s1[:100]}..."')
            _out(f'      Document 2: "{s2[:100]}..."')


def main() -> int:
    """Compare every pair of input documents and report suspicious pairs."""
    parser = argparse.ArgumentParser(
        description="Text Plagiarism Checker - Compare documents for similarity"
    )
    parser.add_argument("files", nargs="*", help="Files to compare")
    parser.add_argument("--dir", "-d", help="Directory containing documents to compare")
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.3,
        help="Similarity threshold for flagging (0-1, default: 0.3)",
    )
    parser.add_argument(
        "--detailed", "-v", action="store_true", help="Show detailed similar passages"
    )

    args = parser.parse_args()

    files = _collect_files(args)
    if len(files) < MIN_DOCUMENTS:
        _out("Error: Need at least 2 files to compare")
        parser.print_help()
        return 1

    _out(f"\n{'=' * 60}")
    _out(f" Plagiarism Check - Analyzing {len(files)} documents")
    _out(f"{'=' * 60}\n")

    documents, filenames = _read_documents(files)
    if len(documents) < MIN_DOCUMENTS:
        _out("Error: Not enough valid documents to compare")
        return 1

    _out("Computing document similarities...\n")
    sim_matrix = compute_similarity_matrix(documents)

    suspicious_pairs = _report_pairs(documents, filenames, sim_matrix, args.threshold)

    if suspicious_pairs:
        _out(
            f"\n⚠️  {len(suspicious_pairs)} pair(s) exceed "
            f"{args.threshold:.0%} similarity threshold\n"
        )
        if args.detailed:
            _print_detailed_passages(files, suspicious_pairs)
    else:
        _out(f"\n✓ No document pairs exceed {args.threshold:.0%} similarity threshold")

    _out("\n" + "=" * 60)
    _out(" Analysis complete")
    _out("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

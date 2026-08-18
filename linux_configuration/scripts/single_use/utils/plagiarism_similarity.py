#!/usr/bin/env python3
"""Document reading and TF-IDF similarity scoring for check_plagiarism.py.

Split out of `check_plagiarism.py` to keep it under the 250-line cap: this
module holds the comparison engine (file reading, text preprocessing, and the
TF-IDF/cosine-similarity computations), `check_plagiarism.py` keeps the CLI
and reporting.

Its third-party imports (numpy, sklearn, nltk) are the plagiarism toolchain's
dependencies, not this repo's, so they are absent from `meta/requirements.txt`
on purpose. Importing them dynamically (rather than with a static `import
nltk`) keeps this module importable -- and lintable -- in an environment
that doesn't have them installed, matching `download_nltk_data.py`'s
extraction.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

#: Cosine similarity above this, for a single sentence pair, is worth reporting
#: as a suspicious passage in --detailed mode.
PASSAGE_SIMILARITY_THRESHOLD = 0.5

nltk = importlib.import_module("nltk")
stopwords = importlib.import_module("nltk.corpus").stopwords
nltk_tokenize = importlib.import_module("nltk.tokenize")
sent_tokenize = nltk_tokenize.sent_tokenize
word_tokenize = nltk_tokenize.word_tokenize
TfidfVectorizer = importlib.import_module(
    "sklearn.feature_extraction.text"
).TfidfVectorizer
cosine_similarity = importlib.import_module(
    "sklearn.metrics.pairwise"
).cosine_similarity

try:
    stopwords.words("english")
except LookupError:
    nltk.download("stopwords", quiet=True)
    nltk.download("punkt", quiet=True)


def _out(line: str = "") -> None:
    sys.stdout.write(line + "\n")


def _read_pdf(filepath: str) -> str:
    try:
        pypdf2 = importlib.import_module("PyPDF2")
    except ImportError:
        _out("Warning: PyPDF2 not installed, cannot read PDF files")
        return ""
    reader = pypdf2.PdfReader(filepath)
    return " ".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(filepath: str) -> str:
    try:
        docx = importlib.import_module("docx")
    except ImportError:
        _out("Warning: python-docx not installed, cannot read DOCX files")
        return ""
    doc = docx.Document(filepath)
    return " ".join(para.text for para in doc.paragraphs)


def read_file(filepath: str) -> str:
    """Read text from a .pdf, .docx, or plain-text file."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _read_pdf(filepath)
    if suffix == ".docx":
        return _read_docx(filepath)
    with path.open(encoding="utf-8", errors="ignore") as f:
        return f.read()


def preprocess_text(text: str) -> str:
    """Lowercase, tokenize, and strip stopwords/non-alphanumerics."""
    text = text.lower()
    try:
        stop_words = set(stopwords.words("english"))
        words = word_tokenize(text)
        words = [w for w in words if w.isalnum() and w not in stop_words]
        return " ".join(words)
    except LookupError:
        return " ".join(text.split())


def compute_similarity_matrix(documents: list[str]) -> list[list[float]]:
    """Compute the TF-IDF cosine similarity matrix for a set of documents.

    Returns a plain nested list, not the numpy array `cosine_similarity`
    produces: numpy is a plagiarism-toolchain dependency the installer
    pip-installs at runtime, deliberately absent from `meta/requirements.txt`,
    so mypy cannot follow it into this repo's type-checked surface
    (`no-any-unimported`). Converting at this boundary keeps every other
    signature in the module concretely typed.
    """
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), min_df=1, max_df=0.95)
    tfidf_matrix = vectorizer.fit_transform(documents)
    matrix: list[list[float]] = cosine_similarity(tfidf_matrix).tolist()
    return matrix


def find_similar_passages(
    text1: str, text2: str, min_words: int = 5
) -> list[tuple[str, str, float]]:
    """Find similar sentence-level passages between two texts."""
    sentences1 = [s for s in sent_tokenize(text1) if len(s.split()) >= min_words]
    sentences2 = [s for s in sent_tokenize(text2) if len(s.split()) >= min_words]

    if not sentences1 or not sentences2:
        return []

    all_sentences = sentences1 + sentences2
    preprocessed = [preprocess_text(s) for s in all_sentences]

    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(preprocessed)
    except ValueError:
        return []

    n1 = len(sentences1)
    similarities = []

    for i, s1 in enumerate(sentences1):
        for j, s2 in enumerate(sentences2):
            sim = cosine_similarity(
                tfidf_matrix[i : i + 1], tfidf_matrix[n1 + j : n1 + j + 1]
            )[0][0]
            if sim > PASSAGE_SIMILARITY_THRESHOLD:
                similarities.append((s1, s2, sim))

    return sorted(similarities, key=lambda x: x[2], reverse=True)

#!/usr/bin/env bash
# Install Free & Open Source Plagiarism Detection Tools for Text
# Suitable for academic work (theses, papers, etc.)
#
# Tools installed:
# 1. Python NLP-based similarity detection (sklearn, NLTK, spaCy)
# 2. Sherlock text plagiarism detector
# 3. Ferret (Java-based, if Java available)
# 4. Optional: WCopyfind via Wine (Windows tool)

set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/plagiarism-tools"
VENV_DIR="${HOME}/.local/share/plagiarism-venv"

echo "=============================================="
echo " Open Source Plagiarism Detection Installer"
echo " For Academic Text (Theses, Papers, etc.)"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }

# Create installation directory
mkdir -p "$INSTALL_DIR"

# ------------------------------------------------------------------------------
# 1. Python-based NLP Plagiarism Detection Environment
# ------------------------------------------------------------------------------
echo ""
echo "=== 1. Installing Python NLP-based Plagiarism Tools ==="

# Check for Python 3
if ! command -v python3 &>/dev/null; then
	error "Python 3 is required but not installed."
	exit 1
fi

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
	echo "Creating Python virtual environment..."
	python3 -m venv "$VENV_DIR"
	success "Virtual environment created at $VENV_DIR"
else
	warn "Virtual environment already exists at $VENV_DIR"
fi

# Activate and install packages
source "$VENV_DIR/bin/activate"

echo "Installing Python packages for text similarity detection..."
pip install --upgrade pip

pip install --progress-bar on \
	scikit-learn \
	nltk \
	spacy \
	gensim \
	numpy \
	pandas \
	python-docx \
	PyPDF2 \
	beautifulsoup4 \
	lxml \
	textdistance \
	fuzzywuzzy \
	python-Levenshtein

success "Python NLP packages installed"

# Download NLTK data
echo "Downloading NLTK data (stopwords, punkt tokenizer)..."
python3 -c "
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
"
success "NLTK data downloaded"

# Download spaCy English model (small)
echo "Downloading spaCy English model..."
python3 -m spacy download en_core_web_sm 2>/dev/null || warn "spaCy model download may need manual install: python -m spacy download en_core_web_sm"
success "spaCy model installed"

# Create a simple plagiarism checker script
cat >"$INSTALL_DIR/check_plagiarism.py" <<'PYEOF'
#!/usr/bin/env python3
"""
Simple Text Plagiarism Checker
Compares documents using multiple similarity algorithms.

Usage:
    python check_plagiarism.py file1.txt file2.txt [file3.txt ...]
    python check_plagiarism.py --dir /path/to/documents/
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

# Ensure NLTK data is available
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)


def read_file(filepath: str) -> str:
    """Read text from various file formats."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == '.pdf':
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            return ' '.join(page.extract_text() or '' for page in reader.pages)
        except ImportError:
            print("Warning: PyPDF2 not installed, cannot read PDF files")
            return ""
    elif suffix == '.docx':
        try:
            from docx import Document
            doc = Document(filepath)
            return ' '.join(para.text for para in doc.paragraphs)
        except ImportError:
            print("Warning: python-docx not installed, cannot read DOCX files")
            return ""
    else:
        # Assume plain text
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()


def preprocess_text(text: str) -> str:
    """Clean and preprocess text for comparison."""
    # Lowercase
    text = text.lower()
    # Tokenize and remove stopwords
    try:
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text)
        words = [w for w in words if w.isalnum() and w not in stop_words]
        return ' '.join(words)
    except Exception:
        # Fallback: simple preprocessing
        return ' '.join(text.split())


def compute_similarity_matrix(documents: List[str]) -> np.ndarray:
    """Compute TF-IDF cosine similarity matrix."""
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),  # Use unigrams, bigrams, trigrams
        min_df=1,
        max_df=0.95
    )
    tfidf_matrix = vectorizer.fit_transform(documents)
    return cosine_similarity(tfidf_matrix)


def find_similar_passages(text1: str, text2: str, min_words: int = 5) -> List[Tuple[str, str, float]]:
    """Find similar sentence-level passages between two texts."""
    sentences1 = sent_tokenize(text1)
    sentences2 = sent_tokenize(text2)

    if not sentences1 or not sentences2:
        return []

    # Filter short sentences
    sentences1 = [s for s in sentences1 if len(s.split()) >= min_words]
    sentences2 = [s for s in sentences2 if len(s.split()) >= min_words]

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
                tfidf_matrix[i:i+1],
                tfidf_matrix[n1+j:n1+j+1]
            )[0][0]
            if sim > 0.5:  # Threshold for suspicious similarity
                similarities.append((s1, s2, sim))

    return sorted(similarities, key=lambda x: x[2], reverse=True)


def main():
    parser = argparse.ArgumentParser(
        description='Text Plagiarism Checker - Compare documents for similarity'
    )
    parser.add_argument('files', nargs='*', help='Files to compare')
    parser.add_argument('--dir', '-d', help='Directory containing documents to compare')
    parser.add_argument('--threshold', '-t', type=float, default=0.3,
                        help='Similarity threshold for flagging (0-1, default: 0.3)')
    parser.add_argument('--detailed', '-v', action='store_true',
                        help='Show detailed similar passages')

    args = parser.parse_args()

    # Collect files
    files = []
    if args.files:
        files.extend(args.files)
    if args.dir:
        dir_path = Path(args.dir)
        for ext in ['*.txt', '*.pdf', '*.docx', '*.md', '*.tex']:
            files.extend(str(f) for f in dir_path.glob(ext))

    if len(files) < 2:
        print("Error: Need at least 2 files to compare")
        parser.print_help()
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f" Plagiarism Check - Analyzing {len(files)} documents")
    print(f"{'='*60}\n")

    # Read and preprocess documents
    documents = []
    filenames = []
    for f in files:
        if os.path.exists(f):
            text = read_file(f)
            if text.strip():
                documents.append(preprocess_text(text))
                filenames.append(os.path.basename(f))
            else:
                print(f"Warning: {f} is empty or unreadable")
        else:
            print(f"Warning: {f} does not exist")

    if len(documents) < 2:
        print("Error: Not enough valid documents to compare")
        sys.exit(1)

    # Compute similarity
    print("Computing document similarities...\n")
    sim_matrix = compute_similarity_matrix(documents)

    # Report results
    print(f"{'Document Pair':<50} {'Similarity':>12}")
    print("-" * 62)

    suspicious_pairs = []
    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            similarity = sim_matrix[i][j]
            pair_name = f"{filenames[i]} <-> {filenames[j]}"

            if similarity >= args.threshold:
                suspicious_pairs.append((i, j, similarity, pair_name))
                print(f"{pair_name:<50} {similarity:>10.1%} ⚠️")
            else:
                print(f"{pair_name:<50} {similarity:>10.1%}")

    print("-" * 62)

    # Summary
    if suspicious_pairs:
        print(f"\n⚠️  {len(suspicious_pairs)} pair(s) exceed {args.threshold:.0%} similarity threshold\n")

        if args.detailed:
            print("\n" + "="*60)
            print(" Detailed Similar Passages")
            print("="*60)

            for i, j, sim, pair_name in suspicious_pairs[:3]:  # Limit to top 3
                print(f"\n{pair_name} ({sim:.1%} similar):")
                print("-" * 40)

                raw_docs = [read_file(files[i]), read_file(files[j])]
                passages = find_similar_passages(raw_docs[0], raw_docs[1])

                for s1, s2, psim in passages[:5]:  # Top 5 passages
                    print(f"\n[{psim:.0%}] Document 1: \"{s1[:100]}...\"")
                    print(f"      Document 2: \"{s2[:100]}...\"")
    else:
        print(f"\n✓ No document pairs exceed {args.threshold:.0%} similarity threshold")

    print("\n" + "="*60)
    print(" Analysis complete")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
PYEOF

chmod +x "$INSTALL_DIR/check_plagiarism.py"
success "Created plagiarism checker script at $INSTALL_DIR/check_plagiarism.py"

# Create convenience wrapper
mkdir -p "$HOME/.local/bin"
cat >"$HOME/.local/bin/plagcheck" <<WRAPEOF
#!/usr/bin/env bash
# Wrapper for plagiarism checker
source "$VENV_DIR/bin/activate"
python "$INSTALL_DIR/check_plagiarism.py" "\$@"
WRAPEOF
chmod +x "$HOME/.local/bin/plagcheck"
success "Created 'plagcheck' command in ~/.local/bin/"

deactivate

# ------------------------------------------------------------------------------
# 2. Sherlock for Text (Clone from GitHub)
# ------------------------------------------------------------------------------
echo ""
echo "=== 2. Installing Sherlock Text Plagiarism Detector ==="

SHERLOCK_DIR="$INSTALL_DIR/sherlock"
if [ ! -d "$SHERLOCK_DIR" ]; then
	# There are several Sherlock implementations; using a popular Python one
	if command -v git &>/dev/null; then
		# Clone a text-based similarity tool
		git clone --depth 1 https://github.com/Zedeldi/sherlock-py.git "$SHERLOCK_DIR" 2>/dev/null || {
			warn "Could not clone sherlock-py, trying alternative..."
			# Alternative: Create a simple n-gram based sherlock
			mkdir -p "$SHERLOCK_DIR"
			cat >"$SHERLOCK_DIR/sherlock.py" <<'SHERLOCKEOF'
#!/usr/bin/env python3
"""
Sherlock - Simple text plagiarism detector using n-gram fingerprinting.
Based on the original Sherlock algorithm.
"""

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path


def tokenize(text: str) -> list:
    """Simple word tokenization."""
    return [w.lower() for w in text.split() if w.isalnum()]


def get_ngrams(tokens: list, n: int = 3) -> list:
    """Generate n-grams from token list."""
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def fingerprint(text: str, ngram_size: int = 3, sample_rate: int = 4) -> set:
    """Create document fingerprint using sampled n-gram hashes."""
    tokens = tokenize(text)
    ngrams = get_ngrams(tokens, ngram_size)

    fingerprints = set()
    for i, ng in enumerate(ngrams):
        if i % sample_rate == 0:  # Sample every nth n-gram
            h = hashlib.md5(''.join(ng).encode()).hexdigest()[:8]
            fingerprints.add(h)

    return fingerprints


def compare_documents(fp1: set, fp2: set) -> float:
    """Jaccard similarity between fingerprints."""
    if not fp1 or not fp2:
        return 0.0
    intersection = len(fp1 & fp2)
    union = len(fp1 | fp2)
    return intersection / union if union > 0 else 0.0


def read_document(filepath: str) -> str:
    """Read document content."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description='Sherlock - Text Plagiarism Detector')
    parser.add_argument('files', nargs='+', help='Files to compare')
    parser.add_argument('--ngram', '-n', type=int, default=3, help='N-gram size (default: 3)')
    parser.add_argument('--threshold', '-t', type=float, default=0.1, help='Similarity threshold')

    args = parser.parse_args()

    if len(args.files) < 2:
        print("Need at least 2 files to compare")
        sys.exit(1)

    # Read and fingerprint documents
    docs = {}
    for f in args.files:
        if os.path.exists(f):
            text = read_document(f)
            docs[f] = fingerprint(text, args.ngram)

    print(f"\nSherlock Plagiarism Analysis")
    print("=" * 50)

    # Compare all pairs
    files = list(docs.keys())
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            sim = compare_documents(docs[files[i]], docs[files[j]])
            name1 = os.path.basename(files[i])
            name2 = os.path.basename(files[j])
            flag = " ⚠️ SUSPICIOUS" if sim >= args.threshold else ""
            print(f"{name1} <-> {name2}: {sim:.1%}{flag}")

    print("=" * 50)


if __name__ == '__main__':
    main()
SHERLOCKEOF
			chmod +x "$SHERLOCK_DIR/sherlock.py"
		}
		success "Sherlock installed at $SHERLOCK_DIR"
	else
		warn "Git not available, skipping Sherlock installation"
	fi
else
	warn "Sherlock already installed at $SHERLOCK_DIR"
fi

# ------------------------------------------------------------------------------
# 3. Ferret (Java-based) - Optional
# ------------------------------------------------------------------------------
echo ""
echo "=== 3. Checking for Ferret (Java-based plagiarism tool) ==="

if command -v java &>/dev/null; then
	FERRET_DIR="$INSTALL_DIR/ferret"
	if [ ! -d "$FERRET_DIR" ]; then
		mkdir -p "$FERRET_DIR"
		echo "Ferret is a Java-based tool from University of Hertfordshire."
		echo "Download manually from: https://homepages.herts.ac.uk/~comqcln/Ferret/"
		echo "Place JAR file in: $FERRET_DIR"
		warn "Ferret requires manual download (academic license)"
	fi
else
	warn "Java not installed, skipping Ferret"
fi

# ------------------------------------------------------------------------------
# 4. WCopyfind via Wine (Optional)
# ------------------------------------------------------------------------------
echo ""
echo "=== 4. WCopyfind Information (Windows tool, needs Wine) ==="

if command -v wine &>/dev/null; then
	echo "Wine is available. WCopyfind can be run via Wine."
	echo "Download from: https://plagiarism.bloomfieldmedia.com/software/wcopyfind/"
	echo "Run with: wine /path/to/WCopyfind.exe"
	warn "WCopyfind requires manual download"
else
	echo "Wine not installed. To use WCopyfind:"
	echo "  1. Install wine: sudo apt install wine  (or equivalent)"
	echo "  2. Download WCopyfind from: https://plagiarism.bloomfieldmedia.com/software/wcopyfind/"
	warn "WCopyfind skipped (Wine not available)"
fi

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------
echo ""
echo "=============================================="
echo " Installation Complete!"
echo "=============================================="
echo ""
echo "Installed tools:"
echo ""
echo "1. Python NLP Plagiarism Checker (TF-IDF, cosine similarity)"
echo "   Usage: plagcheck file1.txt file2.txt"
echo "          plagcheck --dir /path/to/documents/ --detailed"
echo "   Location: $INSTALL_DIR/check_plagiarism.py"
echo ""
echo "2. Sherlock (n-gram fingerprinting)"
echo "   Location: $SHERLOCK_DIR/sherlock.py"
echo ""
echo "3. Python virtual environment with NLP libraries:"
echo "   - scikit-learn (TF-IDF, cosine similarity)"
echo "   - NLTK (tokenization, stopwords)"
echo "   - spaCy (NLP processing)"
echo "   - gensim (document similarity)"
echo "   - textdistance, fuzzywuzzy (string matching)"
echo "   Activate with: source $VENV_DIR/bin/activate"
echo ""
echo "Quick Start:"
echo "  plagcheck thesis_v1.pdf thesis_v2.pdf --detailed"
echo "  plagcheck --dir ./student_papers/ --threshold 0.4"
echo ""
echo "Note: Ensure ~/.local/bin is in your PATH:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
echo ""
echo "=============================================="

# Add to PATH reminder
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
	warn "Add ~/.local/bin to your PATH by adding this to ~/.bashrc or ~/.zshrc:"
	echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

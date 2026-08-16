#!/usr/bin/env python3
"""Download the NLTK corpora the plagiarism tools need.

Extracted from `install_plagiarism_tools.sh`, which used to run this as an
inline `python3 -c` block. Inline Python is invisible to ruff, mypy, pylint,
bandit and pytest, so it lives in its own module instead.

`nltk` is a dependency of the plagiarism toolchain, not of this repo, so it is
absent from `meta/requirements.txt` on purpose. The installer script pip-installs
it immediately before invoking this module, and probes for it first.
"""

from __future__ import annotations

import importlib
import sys

#: Corpora required by the plagiarism checker. `punkt_tab` is the post-3.8.2
#: replacement for `punkt`; both are listed so the script works on either.
CORPORA = (
    "punkt",
    "stopwords",
    "punkt_tab",
    "averaged_perceptron_tagger",
    "wordnet",
)


def main() -> int:
    """Download every corpus, reporting any that fail.

    Returns 1 if any download failed, so the calling shell script's `set -e`
    sees a real failure instead of a silent partial install.
    """
    # Imported dynamically, not at module scope: nltk belongs to the plagiarism
    # toolchain rather than this repo, so it is deliberately absent from
    # meta/requirements.txt and unresolvable to static analysis. The installer
    # pip-installs it immediately before invoking this module.
    try:
        nltk = importlib.import_module("nltk")
    except ImportError:
        sys.stderr.write("error: nltk is not installed\n")
        return 1

    failed = [corpus for corpus in CORPORA if not nltk.download(corpus)]
    if failed:
        sys.stderr.write(f"error: failed to download: {', '.join(failed)}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

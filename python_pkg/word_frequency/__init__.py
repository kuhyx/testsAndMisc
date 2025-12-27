"""Word frequency analyzer package.

This package provides tools for:
1. Analyzing word frequency in text (analyzer module)
2. Finding text excerpts where target words are most prevalent (excerpt_finder module)

Example usage:
    from python_pkg.word_frequency.analyzer import analyze_text, analyze_and_format
    from python_pkg.word_frequency.excerpt_finder import find_best_excerpt

    # Analyze word frequency
    counts = analyze_text("hello world hello")
    print(counts["hello"])  # 2

    # Find excerpt with target words
    results = find_best_excerpt(
        "they went somewhere he and she and the guy",
        target_words=["and", "the"],
        excerpt_length=3,
    )
    print(results[0].excerpt)  # "and she and" or similar
"""

from __future__ import annotations

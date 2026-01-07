#!/usr/bin/env python3
"""Tests for vocabulary_curve C implementation."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

# Path to the C executable
C_EXECUTABLE = (
    Path(__file__).parent.parent.parent.parent
    / "C"
    / "vocabulary_curve"
    / "vocabulary_curve"
)


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    """Create a sample text file for testing."""
    text = """The quick brown fox jumps over the lazy dog.
The fox was very quick and the dog was very lazy.
Quick foxes and lazy dogs are common in stories."""
    filepath = tmp_path / "sample.txt"
    filepath.write_text(text, encoding="utf-8")
    return filepath


@pytest.fixture
def polish_text_file(tmp_path: Path) -> Path:
    """Create a Polish sample text file."""
    text = """Litwo! Ojczyzno moja! Ty jesteś jak zdrowie.
Ile cię trzeba cenić, ten tylko się dowie,
Kto cię stracił. Dziś piękność twą w całej ozdobie
Widzę i opisuję, bo tęsknię po tobie."""
    filepath = tmp_path / "polish.txt"
    filepath.write_text(text, encoding="utf-8")
    return filepath


def run_vocabulary_curve(filepath: Path, max_length: int = 10) -> str:
    """Run the vocabulary_curve executable and return output."""
    if not C_EXECUTABLE.exists():
        pytest.skip(f"C executable not found at {C_EXECUTABLE}")

    result = subprocess.run(
        [str(C_EXECUTABLE), str(filepath), str(max_length)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.stdout


def extract_excerpts_from_output(output: str) -> list[tuple[int, str]]:
    """Extract (length, excerpt) pairs from output."""
    excerpts = []
    lines = output.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("[Length "):
            # Parse length
            length = int(line.split("]")[0].split()[-1])

            # Find excerpt line
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("Excerpt:"):
                i += 1

            if i < len(lines):
                excerpt_line = lines[i].strip()
                # Extract text between quotes
                if '"' in excerpt_line:
                    start = excerpt_line.index('"') + 1
                    end = excerpt_line.rindex('"')
                    excerpt = excerpt_line[start:end]
                    excerpts.append((length, excerpt))
        i += 1

    return excerpts


class TestExcerptValidity:
    """Tests that verify excerpts are actually found in the source text."""

    def test_excerpt_exists_in_source_text(self, sample_text_file: Path) -> None:
        """Test that each excerpt can be found in the source text as contiguous words."""
        import re

        source_text = sample_text_file.read_text(encoding="utf-8").lower()
        source_words = re.findall(r"\b[\w]+\b", source_text)
        output = run_vocabulary_curve(sample_text_file, max_length=10)
        excerpts = extract_excerpts_from_output(output)

        assert len(excerpts) > 0, "No excerpts found in output"

        for length, excerpt in excerpts:
            excerpt_words = excerpt.lower().split()
            # Find this sequence in source_words
            found = False
            for i in range(len(source_words) - len(excerpt_words) + 1):
                if source_words[i : i + len(excerpt_words)] == excerpt_words:
                    found = True
                    break
            assert found, (
                f"Excerpt of length {length} not found in source text:\n"
                f"  Excerpt words: {excerpt_words}\n"
                f"  First 30 source words: {source_words[:30]}"
            )

    def test_excerpt_word_count_matches_length(self, sample_text_file: Path) -> None:
        """Test that excerpt has the expected number of words."""
        output = run_vocabulary_curve(sample_text_file, max_length=10)
        excerpts = extract_excerpts_from_output(output)

        for length, excerpt in excerpts:
            word_count = len(excerpt.split())
            assert (
                word_count == length
            ), f"Expected {length} words, got {word_count}: '{excerpt}'"

    def test_polish_excerpt_exists_in_source(self, polish_text_file: Path) -> None:
        """Test Polish text excerpts are found in source as contiguous words."""
        import re

        source_text = polish_text_file.read_text(encoding="utf-8").lower()
        source_words = re.findall(r"\b[\w]+\b", source_text)
        output = run_vocabulary_curve(polish_text_file, max_length=8)
        excerpts = extract_excerpts_from_output(output)

        assert len(excerpts) > 0, "No excerpts found in output"

        for length, excerpt in excerpts:
            excerpt_words = excerpt.lower().split()
            # Find this sequence in source_words
            found = False
            for i in range(len(source_words) - len(excerpt_words) + 1):
                if source_words[i : i + len(excerpt_words)] == excerpt_words:
                    found = True
                    break
            assert found, (
                f"Polish excerpt of length {length} not found:\n"
                f"  Excerpt words: {excerpt_words}\n"
                f"  Source words: {source_words}"
            )

    def test_excerpt_is_contiguous(self, sample_text_file: Path) -> None:
        """Test that excerpt words appear contiguously in source."""
        import re

        source_text = sample_text_file.read_text(encoding="utf-8").lower()
        # Extract words from source
        source_words = re.findall(r"\b[\w]+\b", source_text)

        output = run_vocabulary_curve(sample_text_file, max_length=5)
        excerpts = extract_excerpts_from_output(output)

        for length, excerpt in excerpts:
            excerpt_words = excerpt.lower().split()

            # Find this sequence in source_words
            found = False
            for i in range(len(source_words) - length + 1):
                if source_words[i : i + length] == excerpt_words:
                    found = True
                    break

            assert found, (
                f"Excerpt words not found as contiguous sequence:\n"
                f"  Excerpt: {excerpt_words}\n"
                f"  First 20 source words: {source_words[:20]}"
            )


class TestVocabNeeded:
    """Tests for vocabulary count calculations."""

    def test_length_1_needs_vocab_1(self, sample_text_file: Path) -> None:
        """Test that a 1-word excerpt needs exactly 1 vocabulary word."""
        output = run_vocabulary_curve(sample_text_file, max_length=1)

        assert "[Length 1] Vocab needed: 1" in output

    def test_vocab_needed_increases_monotonically(self, sample_text_file: Path) -> None:
        """Test that vocab needed never decreases as length increases."""
        output = run_vocabulary_curve(sample_text_file, max_length=10)
        extract_excerpts_from_output(output)

        # Extract vocab needed from output
        prev_vocab = 0
        for line in output.split("\n"):
            if "Vocab needed:" in line:
                # Parse "Vocab needed: X"
                parts = line.split("Vocab needed:")
                if len(parts) > 1:
                    vocab = int(parts[1].split()[0])
                    assert (
                        vocab >= prev_vocab
                    ), f"Vocab decreased from {prev_vocab} to {vocab}"
                    prev_vocab = vocab


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test handling of empty file."""
        filepath = tmp_path / "empty.txt"
        filepath.write_text("", encoding="utf-8")

        if not C_EXECUTABLE.exists():
            pytest.skip("C executable not found")

        result = subprocess.run(
            [str(C_EXECUTABLE), str(filepath), "5"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0 or "No words" in result.stderr

    def test_single_word_file(self, tmp_path: Path) -> None:
        """Test file with single word."""
        filepath = tmp_path / "single.txt"
        filepath.write_text("hello", encoding="utf-8")

        output = run_vocabulary_curve(filepath, max_length=5)

        assert "[Length 1] Vocab needed: 1" in output
        # Should only have 1 length since there's only 1 word
        assert "[Length 2]" not in output

    def test_repeated_word_file(self, tmp_path: Path) -> None:
        """Test file with same word repeated."""
        filepath = tmp_path / "repeated.txt"
        filepath.write_text("hello hello hello hello hello", encoding="utf-8")

        output = run_vocabulary_curve(filepath, max_length=5)

        # All excerpts should need only 1 vocabulary word
        for i in range(1, 6):
            assert f"[Length {i}] Vocab needed: 1" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

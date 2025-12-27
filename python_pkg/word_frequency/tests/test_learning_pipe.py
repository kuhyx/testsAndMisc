"""Tests for word_frequency.learning_pipe module."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from python_pkg.word_frequency.learning_pipe import (
    DEFAULT_STOPWORDS_EN,
    generate_learning_lesson,
    load_stopwords,
    main,
)


class TestLoadStopwords:
    """Tests for load_stopwords function."""

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Test loading stopwords from file."""
        stopwords_file = tmp_path / "stopwords.txt"
        stopwords_file.write_text("word1\nword2\nword3\n", encoding="utf-8")

        result = load_stopwords(stopwords_file)

        assert "word1" in result
        assert "word2" in result
        assert "word3" in result

    def test_load_none_returns_empty(self) -> None:
        """Test that None returns empty frozenset."""
        result = load_stopwords(None)
        assert result == frozenset()

    def test_load_nonexistent_returns_empty(self) -> None:
        """Test that nonexistent file returns empty frozenset."""
        result = load_stopwords("/nonexistent/file.txt")
        assert result == frozenset()

    def test_lowercase_conversion(self, tmp_path: Path) -> None:
        """Test that stopwords are converted to lowercase."""
        stopwords_file = tmp_path / "stopwords.txt"
        stopwords_file.write_text("UPPER\nMixed\nlower\n", encoding="utf-8")

        result = load_stopwords(stopwords_file)

        assert "upper" in result
        assert "mixed" in result
        assert "lower" in result


class TestGenerateLearningLesson:
    """Tests for generate_learning_lesson function."""

    def test_basic_generation(self) -> None:
        """Test basic lesson generation."""
        text = "hello world hello hello world test test test test"
        result = generate_learning_lesson(
            text, batch_size=3, num_batches=1, skip_default_stopwords=True
        )

        assert "LANGUAGE LEARNING LESSON" in result
        assert "VOCABULARY TO LEARN" in result
        assert "test" in result  # Most common word

    def test_multiple_batches(self) -> None:
        """Test generation with multiple batches."""
        text = " ".join(f"word{i}" * (100 - i) for i in range(20))
        result = generate_learning_lesson(
            text, batch_size=5, num_batches=3, skip_default_stopwords=True
        )

        assert "BATCH 1" in result
        assert "BATCH 2" in result
        assert "BATCH 3" in result

    def test_stopwords_filtering(self) -> None:
        """Test that default stopwords are filtered."""
        text = "the the the hello world"
        result = generate_learning_lesson(text, batch_size=5, num_batches=1)

        # "the" should be filtered, "hello" and "world" should appear
        lines = result.split("\n")
        vocab_section = False
        found_words = []
        for line in lines:
            if "VOCABULARY TO LEARN" in line:
                vocab_section = True
            elif vocab_section and ". " in line and "(" in line:
                # Extract word from line like "  1. hello    (1 occurrences..."
                word = line.split(".")[1].split("(")[0].strip()
                found_words.append(word)
            elif vocab_section and "PRACTICE" in line:
                break

        assert "the" not in found_words
        assert "hello" in found_words or "world" in found_words

    def test_skip_default_stopwords(self) -> None:
        """Test disabling default stopword filtering."""
        text = "the the the hello"
        result = generate_learning_lesson(
            text, batch_size=5, num_batches=1, skip_default_stopwords=True
        )

        assert "the" in result.lower()

    def test_numbers_filtered_by_default(self) -> None:
        """Test that numbers are filtered by default."""
        text = "123 123 123 hello world"
        result = generate_learning_lesson(
            text, batch_size=5, num_batches=1, skip_default_stopwords=True
        )

        # Check vocabulary section doesn't include "123"
        lines = result.split("\n")
        for line in lines:
            if ". 123" in line and "occurrences" in line:
                pytest.fail("Number '123' should be filtered from vocabulary")

    def test_numbers_included_when_requested(self) -> None:
        """Test including numbers in vocabulary."""
        text = "123 123 123 hello"
        result = generate_learning_lesson(
            text,
            batch_size=5,
            num_batches=1,
            skip_default_stopwords=True,
            skip_numbers=False,
        )

        assert "123" in result

    def test_coverage_calculation(self) -> None:
        """Test that coverage percentage is calculated."""
        text = "hello hello hello world world test"
        result = generate_learning_lesson(
            text, batch_size=3, num_batches=1, skip_default_stopwords=True
        )

        assert "recognize" in result.lower()
        assert "%" in result

    def test_excerpts_included(self) -> None:
        """Test that practice excerpts are included."""
        text = "hello world hello world hello world test test test"
        result = generate_learning_lesson(
            text,
            batch_size=2,
            num_batches=1,
            excerpt_length=3,
            excerpts_per_batch=2,
            skip_default_stopwords=True,
        )

        assert "PRACTICE EXCERPTS" in result
        assert "Excerpt 1" in result


class TestMain:
    """Tests for main CLI function."""

    def test_basic_text_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test with text input."""
        exit_code = main(
            [
                "--text",
                "hello world hello world test test test",
                "--batch-size",
                "3",
                "--no-default-stopwords",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "LANGUAGE LEARNING LESSON" in captured.out

    def test_file_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test with file input."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world hello world test", encoding="utf-8")

        exit_code = main(
            [
                "--file",
                str(test_file),
                "--batch-size",
                "3",
                "--no-default-stopwords",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "hello" in captured.out.lower()

    def test_output_to_file(self, tmp_path: Path) -> None:
        """Test outputting to file."""
        output_file = tmp_path / "lesson.txt"

        exit_code = main(
            [
                "--text",
                "hello world hello world",
                "--output",
                str(output_file),
                "--no-default-stopwords",
            ]
        )

        assert exit_code == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "LANGUAGE LEARNING LESSON" in content

    def test_custom_stopwords(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test with custom stopwords file."""
        stopwords_file = tmp_path / "stop.txt"
        stopwords_file.write_text("hello\n", encoding="utf-8")

        exit_code = main(
            [
                "--text",
                "hello hello hello world world",
                "--stopwords",
                str(stopwords_file),
                "--no-default-stopwords",
                "--batch-size",
                "5",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        # "hello" should be filtered by custom stopwords

    def test_multiple_batches_option(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --batches option."""
        text = " ".join(f"word{i}" * (50 - i) for i in range(30))
        exit_code = main(
            [
                "--text",
                text,
                "--batch-size",
                "5",
                "--batches",
                "3",
                "--no-default-stopwords",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "BATCH 1" in captured.out
        assert "BATCH 2" in captured.out
        assert "BATCH 3" in captured.out

    def test_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error handling for missing file."""
        exit_code = main(["--file", "/nonexistent/file.txt"])
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "Error" in captured.err


class TestPerformance:
    """Performance tests for learning pipe."""

    def test_large_text_performance(self) -> None:
        """Test performance with large text."""
        # Generate large text with enough unique words for 5 batches
        words = ["word" + str(i) for i in range(500)]
        large_text = " ".join(words * 200)

        start_time = time.perf_counter()
        result = generate_learning_lesson(
            large_text,
            batch_size=50,
            num_batches=5,
            excerpt_length=30,
            skip_default_stopwords=True,
        )
        elapsed = time.perf_counter() - start_time

        assert elapsed < 10.0, f"Generation took {elapsed:.2f}s, expected < 10s"
        assert "BATCH 5" in result


class TestDefaultStopwords:
    """Tests for default stopwords."""

    def test_common_words_in_stopwords(self) -> None:
        """Test that common words are in default stopwords."""
        common = ["the", "a", "an", "and", "or", "but", "in", "on", "is", "are"]
        for word in common:
            assert word in DEFAULT_STOPWORDS_EN

    def test_stopwords_are_lowercase(self) -> None:
        """Test that all stopwords are lowercase."""
        for word in DEFAULT_STOPWORDS_EN:
            assert word == word.lower()

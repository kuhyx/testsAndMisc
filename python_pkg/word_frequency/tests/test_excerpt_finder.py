"""Tests for word_frequency.excerpt_finder module."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from python_pkg.word_frequency.excerpt_finder import (
    ExcerptResult,
    find_best_excerpt,
    find_best_excerpt_with_context,
    format_excerpt_results,
    main,
)


class TestFindBestExcerpt:
    """Tests for find_best_excerpt function."""

    def test_basic_example(self) -> None:
        """Test the example from the user request."""
        text = "they went somewhere he and she and the guy"
        result = find_best_excerpt(text, ["and", "the"], excerpt_length=3)

        assert len(result) == 1
        # Should find an excerpt with 66.67% match (2/3)
        assert result[0].match_count == 2
        assert result[0].match_percentage == pytest.approx(66.67, rel=0.01)

    def test_all_matching_words(self) -> None:
        """Test when all words in excerpt match target words."""
        text = "the and the and the"
        result = find_best_excerpt(text, ["the", "and"], excerpt_length=3)

        assert len(result) == 1
        assert result[0].match_count == 3
        assert result[0].match_percentage == 100.0

    def test_no_matching_words(self) -> None:
        """Test when no words match target words."""
        text = "hello world foo bar"
        result = find_best_excerpt(text, ["xyz", "abc"], excerpt_length=2)

        assert len(result) == 1
        assert result[0].match_count == 0
        assert result[0].match_percentage == 0.0

    def test_top_n_results(self) -> None:
        """Test getting multiple top results."""
        text = "they went somewhere he and she and the guy"
        result = find_best_excerpt(text, ["and", "the"], excerpt_length=3, top_n=5)

        # Should have multiple results
        assert len(result) >= 3
        # First results should have higher or equal match counts than later ones
        for i in range(len(result) - 1):
            assert result[i].match_count >= result[i + 1].match_count

    def test_case_insensitive_default(self) -> None:
        """Test case-insensitive matching by default."""
        text = "THE And THE and THE"
        result = find_best_excerpt(text, ["the", "AND"], excerpt_length=3)

        assert result[0].match_count == 3

    def test_case_sensitive(self) -> None:
        """Test case-sensitive matching."""
        text = "THE And THE and THE"
        result = find_best_excerpt(
            text, ["the", "and"], excerpt_length=3, case_sensitive=True
        )

        # "THE" won't match "the", "And" won't match "and"
        # Only "and" matches in position 3
        assert result[0].match_count < 3

    def test_empty_text(self) -> None:
        """Test with empty text."""
        result = find_best_excerpt("", ["the"], excerpt_length=3)
        assert result == []

    def test_text_shorter_than_excerpt(self) -> None:
        """Test when text is shorter than requested excerpt."""
        result = find_best_excerpt("hello world", ["hello"], excerpt_length=5)
        assert result == []

    def test_zero_excerpt_length(self) -> None:
        """Test with zero excerpt length."""
        result = find_best_excerpt("hello world", ["hello"], excerpt_length=0)
        assert result == []

    def test_negative_excerpt_length(self) -> None:
        """Test with negative excerpt length."""
        result = find_best_excerpt("hello world", ["hello"], excerpt_length=-1)
        assert result == []

    def test_excerpt_at_text_boundaries(self) -> None:
        """Test that excerpts at start and end of text are found."""
        text = "the the the middle words here end end end"
        result = find_best_excerpt(text, ["the"], excerpt_length=3, top_n=10)

        # Check that we find the "the the the" at the start
        excerpts = [r.excerpt for r in result]
        assert "the the the" in excerpts

    def test_unicode_words(self) -> None:
        """Test with Polish/unicode words."""
        text = "zażółć gęślą jaźń i w się nie"
        result = find_best_excerpt(text, ["zażółć", "jaźń"], excerpt_length=3)

        assert len(result) == 1
        # "zażółć gęślą jaźń" should have 2 matches
        assert result[0].match_count == 2

    def test_result_structure(self) -> None:
        """Test that result has correct structure."""
        text = "hello world test"
        result = find_best_excerpt(text, ["hello"], excerpt_length=2)

        assert len(result) == 1
        assert isinstance(result[0], ExcerptResult)
        assert isinstance(result[0].excerpt, str)
        assert isinstance(result[0].words, list)
        assert isinstance(result[0].start_index, int)
        assert isinstance(result[0].end_index, int)
        assert isinstance(result[0].match_count, int)
        assert isinstance(result[0].match_percentage, float)

    def test_word_indices(self) -> None:
        """Test that word indices are correct."""
        text = "a b c d e"
        result = find_best_excerpt(text, ["c"], excerpt_length=1)

        # "c" is at index 2
        assert result[0].start_index == 2
        assert result[0].end_index == 3
        assert result[0].excerpt == "c"


class TestFindBestExcerptWithContext:
    """Tests for find_best_excerpt_with_context function."""

    def test_no_context(self) -> None:
        """Test with zero context (should behave like find_best_excerpt)."""
        text = "a b c d e f g"
        result = find_best_excerpt_with_context(
            text, ["c"], excerpt_length=1, context_words=0
        )

        assert result[0].excerpt == "c"

    def test_with_context(self) -> None:
        """Test with context words."""
        text = "a b c d e f g"
        result = find_best_excerpt_with_context(
            text, ["d"], excerpt_length=1, context_words=2
        )

        # "d" at index 3, with context should include 2 words before and after
        # Result should be "b c d e f"
        assert "d" in result[0].excerpt
        assert len(result[0].words) == 5

    def test_context_at_start(self) -> None:
        """Test context doesn't go before start of text."""
        text = "a b c d e"
        result = find_best_excerpt_with_context(
            text, ["a"], excerpt_length=1, context_words=3
        )

        # Can't go before "a", so just get words after
        assert result[0].start_index == 0
        assert result[0].words[0] == "a"

    def test_context_at_end(self) -> None:
        """Test context doesn't go beyond end of text."""
        text = "a b c d e"
        result = find_best_excerpt_with_context(
            text, ["e"], excerpt_length=1, context_words=3
        )

        # Can't go beyond "e"
        assert result[0].words[-1] == "e"


class TestFormatExcerptResults:
    """Tests for format_excerpt_results function."""

    def test_single_result(self) -> None:
        """Test formatting a single result."""
        results = [
            ExcerptResult(
                excerpt="hello world",
                words=["hello", "world"],
                start_index=0,
                end_index=2,
                match_count=1,
                match_percentage=50.0,
            )
        ]
        output = format_excerpt_results(results, ["hello"])

        assert "hello" in output
        assert "50.00%" in output
        assert "hello world" in output

    def test_multiple_results(self) -> None:
        """Test formatting multiple results."""
        results = [
            ExcerptResult(
                excerpt="a b",
                words=["a", "b"],
                start_index=0,
                end_index=2,
                match_count=2,
                match_percentage=100.0,
            ),
            ExcerptResult(
                excerpt="c d",
                words=["c", "d"],
                start_index=2,
                end_index=4,
                match_count=1,
                match_percentage=50.0,
            ),
        ]
        output = format_excerpt_results(results, ["a", "b"])

        assert "Result #1" in output
        assert "Result #2" in output

    def test_empty_results(self) -> None:
        """Test formatting empty results."""
        output = format_excerpt_results([], ["hello"])
        assert "No excerpts found" in output


class TestMain:
    """Tests for main CLI function."""

    def test_text_and_words_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --text and --words options."""
        exit_code = main(
            ["--text", "hello world hello", "--words", "hello", "--length", "2"]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "hello" in captured.out

    def test_file_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --file input option."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world hello world", encoding="utf-8")

        exit_code = main(
            ["--file", str(test_file), "--words", "hello", "--length", "2"]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "hello" in captured.out

    def test_words_file_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --words-file option."""
        text_file = tmp_path / "text.txt"
        words_file = tmp_path / "words.txt"
        text_file.write_text("hello world hello world", encoding="utf-8")
        words_file.write_text("hello\nworld\n", encoding="utf-8")

        exit_code = main(
            [
                "--file",
                str(text_file),
                "--words-file",
                str(words_file),
                "--length",
                "2",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "100.00%" in captured.out  # Both words match

    def test_top_option(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --top option."""
        exit_code = main(
            [
                "--text",
                "a b c d e f",
                "--words",
                "a",
                "b",
                "--length",
                "2",
                "--top",
                "3",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        # Should show multiple results
        assert "Result #1" in captured.out

    def test_context_option(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --context option."""
        exit_code = main(
            [
                "--text",
                "a b c d e f g",
                "--words",
                "d",
                "--length",
                "1",
                "--context",
                "2",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        # Excerpt should include context words

    def test_case_sensitive_option(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --case-sensitive option."""
        exit_code = main(
            [
                "--text",
                "Hello HELLO hello",
                "--words",
                "hello",
                "--length",
                "1",
                "--case-sensitive",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        # Only lowercase "hello" should match

    def test_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error handling for missing file."""
        exit_code = main(
            ["--file", "/nonexistent/file.txt", "--words", "hello", "--length", "2"]
        )
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "Error" in captured.err

    def test_empty_words_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test error when words file is empty."""
        text_file = tmp_path / "text.txt"
        words_file = tmp_path / "words.txt"
        text_file.write_text("hello world", encoding="utf-8")
        words_file.write_text("", encoding="utf-8")

        exit_code = main(
            [
                "--file",
                str(text_file),
                "--words-file",
                str(words_file),
                "--length",
                "2",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "No target words" in captured.err


class TestPerformance:
    """Performance tests for excerpt finder."""

    def test_large_text_performance(self) -> None:
        """Test that finding excerpts in large text completes quickly."""
        # Generate large text (~100k words)
        words = ["the", "and", "of", "to", "in", "a", "that", "is", "was", "for"]
        large_text = " ".join(words * 10000)

        target_words = ["the", "and", "of"]

        start_time = time.perf_counter()
        result = find_best_excerpt(
            large_text, target_words, excerpt_length=100, top_n=10
        )
        elapsed = time.perf_counter() - start_time

        assert elapsed < 5.0, f"Search took {elapsed:.2f}s, expected < 5s"
        assert len(result) > 0

    def test_many_target_words_performance(self) -> None:
        """Test performance with many target words."""
        # Generate text
        text_words = [f"word{i}" for i in range(1000)] * 100
        large_text = " ".join(text_words)

        # Many target words
        target_words = [f"word{i}" for i in range(500)]

        start_time = time.perf_counter()
        result = find_best_excerpt(large_text, target_words, excerpt_length=50, top_n=5)
        elapsed = time.perf_counter() - start_time

        assert elapsed < 10.0, f"Search took {elapsed:.2f}s, expected < 10s"
        assert len(result) > 0

    def test_long_excerpt_performance(self) -> None:
        """Test performance with long excerpt length."""
        words = ["a", "b", "c", "d", "e"] * 10000
        large_text = " ".join(words)

        start_time = time.perf_counter()
        result = find_best_excerpt(large_text, ["a", "b"], excerpt_length=1000, top_n=5)
        elapsed = time.perf_counter() - start_time

        assert elapsed < 5.0, f"Search took {elapsed:.2f}s, expected < 5s"
        assert len(result) > 0

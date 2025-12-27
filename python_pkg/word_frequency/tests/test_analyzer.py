"""Tests for word_frequency.analyzer module."""

from __future__ import annotations

import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_pkg.word_frequency.analyzer import (
    analyze_and_format,
    analyze_text,
    extract_words,
    format_results,
    main,
    read_file,
    read_files,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class TestExtractWords:
    """Tests for extract_words function."""

    def test_basic_extraction(self) -> None:
        """Test basic word extraction."""
        text = "Hello world"
        result = extract_words(text)
        assert result == ["hello", "world"]

    def test_case_insensitive_default(self) -> None:
        """Test that extraction is case-insensitive by default."""
        text = "Hello WORLD HeLLo"
        result = extract_words(text)
        assert result == ["hello", "world", "hello"]

    def test_case_sensitive(self) -> None:
        """Test case-sensitive extraction."""
        text = "Hello WORLD HeLLo"
        result = extract_words(text, case_sensitive=True)
        assert result == ["Hello", "WORLD", "HeLLo"]

    def test_unicode_words(self) -> None:
        """Test extraction of unicode words (Polish, Latin accents)."""
        text = "zażółć gęślą jaźń"
        result = extract_words(text)
        assert result == ["zażółć", "gęślą", "jaźń"]

    def test_punctuation_removal(self) -> None:
        """Test that punctuation is not included in words."""
        text = "Hello, world! How are you?"
        result = extract_words(text)
        assert result == ["hello", "world", "how", "are", "you"]

    def test_numbers_included(self) -> None:
        """Test that numbers are included as words."""
        text = "There are 123 apples and 456 oranges"
        result = extract_words(text)
        assert "123" in result
        assert "456" in result

    def test_empty_string(self) -> None:
        """Test extraction from empty string."""
        result = extract_words("")
        assert result == []

    def test_only_punctuation(self) -> None:
        """Test extraction from string with only punctuation."""
        result = extract_words("!@#$%^&*()")
        assert result == []

    def test_hyphenated_words(self) -> None:
        """Test handling of hyphenated words (split into parts)."""
        text = "well-known self-aware"
        result = extract_words(text)
        # Hyphens act as word boundaries with \b
        assert "well" in result
        assert "known" in result


class TestAnalyzeText:
    """Tests for analyze_text function."""

    def test_basic_counting(self) -> None:
        """Test basic word counting."""
        text = "hello world hello"
        result = analyze_text(text)
        assert result["hello"] == 2
        assert result["world"] == 1

    def test_case_insensitive_counting(self) -> None:
        """Test case-insensitive counting."""
        text = "Hello HELLO hello"
        result = analyze_text(text)
        assert result["hello"] == 3

    def test_case_sensitive_counting(self) -> None:
        """Test case-sensitive counting."""
        text = "Hello HELLO hello"
        result = analyze_text(text, case_sensitive=True)
        assert result["Hello"] == 1
        assert result["HELLO"] == 1
        assert result["hello"] == 1

    def test_returns_counter(self) -> None:
        """Test that result is a Counter object."""
        result = analyze_text("test")
        assert isinstance(result, Counter)

    def test_empty_text(self) -> None:
        """Test analysis of empty text."""
        result = analyze_text("")
        assert len(result) == 0


class TestReadFile:
    """Tests for read_file function."""

    def test_read_existing_file(self, tmp_path: Path) -> None:
        """Test reading an existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")
        result = read_file(test_file)
        assert result == "Hello world"

    def test_read_utf8_content(self, tmp_path: Path) -> None:
        """Test reading UTF-8 content with special characters."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("zażółć gęślą jaźń", encoding="utf-8")
        result = read_file(test_file)
        assert result == "zażółć gęślą jaźń"

    def test_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            read_file("/nonexistent/path/file.txt")


class TestReadFiles:
    """Tests for read_files function."""

    def test_read_multiple_files(self, tmp_path: Path) -> None:
        """Test reading multiple files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Hello", encoding="utf-8")
        file2.write_text("World", encoding="utf-8")
        result = read_files([file1, file2])
        assert "Hello" in result
        assert "World" in result

    def test_empty_list(self) -> None:
        """Test reading empty list of files."""
        result = read_files([])
        assert result == ""


class TestFormatResults:
    """Tests for format_results function."""

    def test_basic_formatting(self) -> None:
        """Test basic result formatting."""
        counter: Counter[str] = Counter({"hello": 3, "world": 2})
        result = format_results(counter)
        assert "Total words: 5" in result
        assert "Unique words: 2" in result
        assert "hello" in result
        assert "world" in result
        assert "60.00%" in result  # hello percentage
        assert "40.00%" in result  # world percentage

    def test_top_n_limit(self) -> None:
        """Test limiting results to top N."""
        counter: Counter[str] = Counter({"a": 10, "b": 5, "c": 3, "d": 1})
        result = format_results(counter, top_n=2)
        assert "a" in result
        assert "b" in result
        # c and d should not appear in the data rows
        lines = result.split("\n")
        data_lines = [line for line in lines if line.strip() and "%" in line]
        assert len(data_lines) == 2

    def test_empty_counter(self) -> None:
        """Test formatting empty counter."""
        counter: Counter[str] = Counter()
        result = format_results(counter)
        assert "No words found" in result


class TestAnalyzeAndFormat:
    """Tests for analyze_and_format function."""

    def test_full_pipeline(self) -> None:
        """Test the full analyze and format pipeline."""
        text = "hello world hello"
        result = analyze_and_format(text)
        assert "Total words: 3" in result
        assert "hello" in result
        assert "66.67%" in result  # hello appears 2/3 times


class TestMain:
    """Tests for main CLI function."""

    def test_text_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --text input option."""
        exit_code = main(["--text", "hello world hello"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "hello" in captured.out
        assert "world" in captured.out

    def test_file_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --file input option."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world hello", encoding="utf-8")
        exit_code = main(["--file", str(test_file)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "hello" in captured.out

    def test_files_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --files input option."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("hello hello", encoding="utf-8")
        file2.write_text("world world world", encoding="utf-8")
        exit_code = main(["--files", str(file1), str(file2)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "hello" in captured.out
        assert "world" in captured.out

    def test_top_n_option(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --top option to limit results."""
        exit_code = main(["--text", "a a a b b c d e f g", "--top", "2"])
        captured = capsys.readouterr()
        assert exit_code == 0
        # Count data lines with percentages
        lines = [line for line in captured.out.split("\n") if "%" in line]
        assert len(lines) == 2

    def test_case_sensitive_option(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --case-sensitive option."""
        exit_code = main(["--text", "Hello HELLO hello", "--case-sensitive"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Unique words: 3" in captured.out

    def test_file_not_found_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error handling for missing file."""
        exit_code = main(["--file", "/nonexistent/file.txt"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "Error" in captured.err


class TestPerformance:
    """Performance tests for word frequency analyzer."""

    def test_large_text_performance(self) -> None:
        """Test that analyzing large text with 10k top words completes in < 10s."""
        # Generate a large text with many unique words
        # We'll create ~100k words to ensure a good stress test
        words = [f"word{i}" for i in range(10000)]
        # Repeat each word a varying number of times
        text_parts = []
        for i, word in enumerate(words):
            # More common words appear more often
            count = 10000 - i
            text_parts.extend([word] * max(1, count // 100))

        large_text = " ".join(text_parts)

        start_time = time.perf_counter()
        result = analyze_and_format(large_text, top_n=10000)
        elapsed = time.perf_counter() - start_time

        assert elapsed < 10.0, f"Analysis took {elapsed:.2f}s, expected < 10s"
        assert "word0" in result  # Most common word should be present

    def test_bible_sized_text_performance(self, tmp_path: Path) -> None:
        """Test with Bible-sized text (~800k words)."""
        # Generate text similar in size to the Bible
        base_words = ["the", "and", "of", "to", "in", "a", "that", "is", "was", "for"]
        text_parts = []
        for _ in range(80000):  # ~800k words total
            text_parts.extend(base_words)

        large_text = " ".join(text_parts)

        start_time = time.perf_counter()
        result = analyze_and_format(large_text, top_n=10000)
        elapsed = time.perf_counter() - start_time

        assert elapsed < 10.0, f"Analysis took {elapsed:.2f}s, expected < 10s"
        assert "the" in result

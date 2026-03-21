"""Tests for word_frequency._parsing module."""

from __future__ import annotations

from python_pkg.word_frequency._parsing import (
    _parse_excerpt_lines,
    _parse_target_length_block,
    _parse_vocab_dump,
    parse_inverse_mode_output,
    parse_vocabulary_curve_output,
)


class TestParseVocabDump:
    """Tests for _parse_vocab_dump."""

    def test_parses_vocab(self) -> None:
        lines = [
            "VOCAB_DUMP_START",
            "hello;1",
            "world;2",
            "VOCAB_DUMP_END",
        ]
        result = _parse_vocab_dump(lines)
        assert result == [("hello", 1), ("world", 2)]

    def test_no_dump_section(self) -> None:
        lines = ["some random output", "more stuff"]
        result = _parse_vocab_dump(lines)
        assert result == []

    def test_invalid_rank(self) -> None:
        lines = [
            "VOCAB_DUMP_START",
            "hello;notanumber",
            "world;2",
            "VOCAB_DUMP_END",
        ]
        result = _parse_vocab_dump(lines)
        assert result == [("world", 2)]

    def test_wrong_parts_count(self) -> None:
        lines = [
            "VOCAB_DUMP_START",
            "hello;1;extra",
            "world;2",
            "VOCAB_DUMP_END",
        ]
        result = _parse_vocab_dump(lines)
        assert result == [("world", 2)]

    def test_line_without_semicolon(self) -> None:
        lines = [
            "VOCAB_DUMP_START",
            "no semicolon here",
            "world;2",
            "VOCAB_DUMP_END",
        ]
        result = _parse_vocab_dump(lines)
        assert result == [("world", 2)]


class TestParseExcerptLines:
    """Tests for _parse_excerpt_lines."""

    def test_single_line_with_quotes(self) -> None:
        lines = ['"hello world"']
        result = _parse_excerpt_lines(lines, 0)
        assert result == "hello world"

    def test_multi_line(self) -> None:
        lines = ['"hello', 'world"']
        result = _parse_excerpt_lines(lines, 0)
        assert result == "hello world"

    def test_with_leading_quote(self) -> None:
        lines = ['"hello world"']
        result = _parse_excerpt_lines(lines, 0)
        assert "hello world" in result

    def test_no_ending_quote(self) -> None:
        lines = ['"hello world']
        result = _parse_excerpt_lines(lines, 0)
        assert "hello world" in result


class TestParseInverseModeOutput:
    """Tests for parse_inverse_mode_output."""

    def test_full_output(self) -> None:
        output = """LONGEST EXCERPT: 5 words using top 10 vocabulary
Excerpt:
"hello world foo bar baz"
Rarest word used: baz (#5)

VOCAB_DUMP_START
hello;1
world;2
VOCAB_DUMP_END
"""
        excerpt, length, max_rank, vocab = parse_inverse_mode_output(output)
        assert length == 5
        assert excerpt == "hello world foo bar baz"
        assert max_rank == 5
        assert vocab == [("hello", 1), ("world", 2)]

    def test_no_rarest_word(self) -> None:
        output = """LONGEST EXCERPT: 3 words
Excerpt:
"hello world foo"
"""
        excerpt, length, max_rank, vocab = parse_inverse_mode_output(output)
        assert length == 3
        assert max_rank == 0

    def test_empty_output(self) -> None:
        excerpt, length, max_rank, vocab = parse_inverse_mode_output("")
        assert excerpt == ""
        assert length == 0
        assert max_rank == 0
        assert vocab == []

    def test_short_longest_excerpt_line(self) -> None:
        output = "LONGEST EXCERPT: 0"
        excerpt, length, max_rank, vocab = parse_inverse_mode_output(output)
        assert length == 0

    def test_too_few_parts_in_longest_excerpt(self) -> None:
        output = "LONGEST EXCERPT:"
        excerpt, length, max_rank, vocab = parse_inverse_mode_output(output)
        assert length == 0

    def test_rarest_word_without_hash_number(self) -> None:
        output = "Rarest word used: unknown"
        excerpt, length, max_rank, vocab = parse_inverse_mode_output(output)
        assert max_rank == 0


class TestParseTargetLengthBlock:
    """Tests for _parse_target_length_block."""

    def test_parses_block(self) -> None:
        lines = [
            "[Length 3] Vocab needed: 2",
            '  Excerpt: "hello world foo"',
            "  Words: hello(#1), world(#2)",
        ]
        excerpt, words = _parse_target_length_block(lines, 3)
        assert excerpt == "hello world foo"
        assert ("hello", 1) in words
        assert ("world", 2) in words

    def test_no_matching_length(self) -> None:
        lines = [
            "[Length 5] Vocab needed: 2",
            '  Excerpt: "hello"',
            "  Words: hello(#1)",
        ]
        excerpt, words = _parse_target_length_block(lines, 999)
        assert excerpt == ""
        assert words == []

    def test_no_excerpt_line(self) -> None:
        lines = [
            "[Length 3] Vocab needed: 2",
            "  Words: hello(#1)",
        ]
        excerpt, words = _parse_target_length_block(lines, 3)
        assert excerpt == ""

    def test_no_words_line(self) -> None:
        lines = [
            "[Length 3] Vocab needed: 2",
            '  Excerpt: "hello world"',
        ]
        excerpt, words = _parse_target_length_block(lines, 3)
        assert excerpt == "hello world"
        assert words == []

    def test_excerpt_without_quotes(self) -> None:
        lines = [
            "[Length 3] Vocab needed: 2",
            "  Excerpt: hello world",
            "  Words: hello(#1)",
        ]
        excerpt, words = _parse_target_length_block(lines, 3)
        assert excerpt == ""
        assert ("hello", 1) in words

    def test_excerpt_found_but_no_words_before_eof(self) -> None:
        lines = [
            "[Length 3] Vocab needed: 2",
            '  Excerpt: "hello"',
            "  some random line",
        ]
        excerpt, words = _parse_target_length_block(lines, 3)
        assert excerpt == "hello"
        assert words == []


class TestParseVocabularyCurveOutput:
    """Tests for parse_vocabulary_curve_output."""

    def test_with_vocab_dump(self) -> None:
        output = """[Length 2] Vocab needed: 2
  Excerpt: "hello world"
  Words: hello(#1), world(#2)

VOCAB_DUMP_START
hello;1
world;2
foo;3
VOCAB_DUMP_END
"""
        excerpt, words, all_vocab = parse_vocabulary_curve_output(output, 2)
        assert excerpt == "hello world"
        assert len(words) == 2
        assert len(all_vocab) == 3

    def test_without_vocab_dump(self) -> None:
        output = """[Length 2] Vocab needed: 2
  Excerpt: "hello world"
  Words: hello(#1), world(#2)
"""
        excerpt, words, all_vocab = parse_vocabulary_curve_output(output, 2)
        assert excerpt == "hello world"
        assert len(words) == 2
        assert all_vocab == []

"""Tests for analyze_chess_game utility and scoring functions."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, mock_open, patch

import chess
import chess.engine
import pytest

from python_pkg.stockfish_analysis._move_analysis import (
    classify_cp_loss,
    fmt_eval,
    score_to_cp,
)
from python_pkg.stockfish_analysis.analyze_chess_game import (
    _auto_hash_mb,
    _detect_total_mem_mb,
    _parse_hash_mb,
    _parse_threads,
    extract_pgn_text,
)


class TestExtractPgnText:
    """Tests for extract_pgn_text function."""

    def test_extract_pgn_after_marker(self) -> None:
        """Test extraction after PGN: marker."""
        raw = "Some log stuff\nPGN:\n1. e4 e5 2. Nf3 Nc6"
        result = extract_pgn_text(raw)
        assert result == "1. e4 e5 2. Nf3 Nc6"

    def test_extract_pgn_from_tag_line(self) -> None:
        """Test extraction from first PGN tag."""
        raw = 'Log header\n[Event "Test"]\n1. e4 e5'
        result = extract_pgn_text(raw)
        assert result is not None
        assert '[Event "Test"]' in result
        assert "1. e4 e5" in result

    def test_extract_pgn_from_move_number(self) -> None:
        """Test extraction from first move number."""
        raw = "Some text\n1. e4 e5 2. Nf3"
        result = extract_pgn_text(raw)
        assert result == "1. e4 e5 2. Nf3"

    def test_extract_pgn_no_match(self) -> None:
        """Test extraction returns None when no PGN found."""
        raw = "No PGN content here\nJust some text"
        result = extract_pgn_text(raw)
        assert result is None

    def test_extract_pgn_empty_after_marker(self) -> None:
        """Test extraction with empty content after marker."""
        # Need double newline so splitlines creates an empty second element
        raw = "PGN:\n\n"
        result = extract_pgn_text(raw)
        # Should fall through to tag check, then move check, then None
        assert result is None

    def test_extract_pgn_empty_tag_line(self) -> None:
        """Test extraction when tag line at end results in empty pgn."""
        # Tag line is last line so join is just that line, which is non-empty
        raw = "text\n[ ]"
        result = extract_pgn_text(raw)
        assert result == "[ ]"

    def test_extract_pgn_pgn_marker_followed_by_tag(self) -> None:
        """Test extraction when PGN: marker is followed by tag (empty after)."""
        # PGN: marker with only whitespace after, then has tag
        raw = "PGN:\n   \n[Event]"
        result = extract_pgn_text(raw)
        # Whitespace lines collapse to just "[Event]"
        assert "[Event]" in (result or "")

    def test_extract_pgn_only_whitespace_after_tag(self) -> None:
        """Test extraction when only whitespace after tag line."""
        raw = "[Event]\n   \n  "
        result = extract_pgn_text(raw)
        # Strip makes it non-empty since [Event] is included
        assert result is not None

    def test_extract_pgn_only_whitespace_after_move(self) -> None:
        """Test extraction when move line followed by whitespace only."""
        raw = "text\n1.  \n  "
        result = extract_pgn_text(raw)
        # "1." followed by whitespace is valid
        assert result is not None


class TestScoreToCp:
    """Tests for score_to_cp function."""

    def test_score_to_cp_centipawn(self) -> None:
        """Test centipawn score conversion."""
        mock_score = MagicMock(spec=chess.engine.PovScore)
        mock_pov = MagicMock()
        mock_pov.is_mate.return_value = False
        mock_pov.score.return_value = 150
        mock_score.pov.return_value = mock_pov

        cp, mate = score_to_cp(mock_score, pov_white=True)
        assert cp == 150
        assert mate is None

    def test_score_to_cp_mate(self) -> None:
        """Test mate score conversion."""
        mock_score = MagicMock(spec=chess.engine.PovScore)
        mock_pov = MagicMock()
        mock_pov.is_mate.return_value = True
        mock_pov.mate.return_value = 3
        mock_score.pov.return_value = mock_pov

        cp, mate = score_to_cp(mock_score, pov_white=True)
        assert cp is None
        assert mate == 3


class TestClassifyCpLoss:
    """Tests for classify_cp_loss function."""

    def test_classify_best(self) -> None:
        """Test classification of best move."""
        assert classify_cp_loss(5) == "Best"
        assert classify_cp_loss(10) == "Best"

    def test_classify_excellent(self) -> None:
        """Test classification of excellent move."""
        assert classify_cp_loss(15) == "Excellent"
        assert classify_cp_loss(20) == "Excellent"

    def test_classify_good(self) -> None:
        """Test classification of good move."""
        assert classify_cp_loss(30) == "Good"
        assert classify_cp_loss(50) == "Good"

    def test_classify_inaccuracy(self) -> None:
        """Test classification of inaccuracy."""
        assert classify_cp_loss(60) == "Inaccuracy"
        assert classify_cp_loss(99) == "Inaccuracy"

    def test_classify_mistake(self) -> None:
        """Test classification of mistake."""
        assert classify_cp_loss(150) == "Mistake"
        assert classify_cp_loss(299) == "Mistake"

    def test_classify_blunder(self) -> None:
        """Test classification of blunder."""
        assert classify_cp_loss(300) == "Blunder"
        assert classify_cp_loss(500) == "Blunder"

    def test_classify_unknown(self) -> None:
        """Test classification of unknown loss."""
        assert classify_cp_loss(None) == "Unknown"


class TestFmtEval:
    """Tests for fmt_eval function."""

    def test_fmt_eval_mate(self) -> None:
        """Test formatting mate score."""
        assert fmt_eval(None, 3) == "M+3"
        assert fmt_eval(None, -2) == "M-2"

    def test_fmt_eval_centipawn(self) -> None:
        """Test formatting centipawn score."""
        assert fmt_eval(150, None) == "+1.50"
        assert fmt_eval(-200, None) == "-2.00"
        assert fmt_eval(0, None) == "+0.00"

    def test_fmt_eval_unknown(self) -> None:
        """Test formatting unknown score."""
        assert fmt_eval(None, None) == "?"


class TestParseThreads:
    """Tests for _parse_threads function."""

    def test_parse_threads_auto(self) -> None:
        """Test auto thread detection."""
        assert _parse_threads("auto") is None
        assert _parse_threads("max") is None
        assert _parse_threads("") is None

    def test_parse_threads_integer(self) -> None:
        """Test integer thread count."""
        assert _parse_threads("4") == 4
        assert _parse_threads("16") == 16

    def test_parse_threads_minimum(self) -> None:
        """Test minimum thread count enforced."""
        assert _parse_threads("0") == 1
        assert _parse_threads("-1") == 1

    def test_parse_threads_invalid(self) -> None:
        """Test invalid thread value."""
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_threads("invalid")


class TestParseHashMb:
    """Tests for _parse_hash_mb function."""

    def test_parse_hash_auto(self) -> None:
        """Test auto hash detection."""
        assert _parse_hash_mb("auto") is None
        assert _parse_hash_mb("max") is None
        assert _parse_hash_mb("") is None

    def test_parse_hash_integer(self) -> None:
        """Test integer hash size."""
        assert _parse_hash_mb("512") == 512
        assert _parse_hash_mb("2048") == 2048

    def test_parse_hash_minimum(self) -> None:
        """Test minimum hash size enforced."""
        assert _parse_hash_mb("8") == 16

    def test_parse_hash_invalid(self) -> None:
        """Test invalid hash value."""
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_hash_mb("invalid")


class TestDetectTotalMemMb:
    """Tests for _detect_total_mem_mb function."""

    def test_detect_mem_with_psutil(self) -> None:
        """Test memory detection with psutil."""
        mock_vm = MagicMock()
        mock_vm.total = 16 * 1024 * 1024 * 1024  # 16 GB

        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game.psutil"
        ) as mock_psutil:
            mock_psutil.virtual_memory.return_value = mock_vm
            result = _detect_total_mem_mb()
            assert result == 16384

    def test_detect_mem_psutil_exception(self) -> None:
        """Test memory detection when psutil fails - falls back to /proc."""
        with (
            patch(
                "python_pkg.stockfish_analysis.analyze_chess_game.psutil"
            ) as mock_psutil,
            patch("python_pkg.stockfish_analysis.analyze_chess_game.Path") as mock_path,
        ):
            mock_psutil.virtual_memory.side_effect = RuntimeError("fail")
            # Also make /proc/meminfo fail so we get None
            mock_path.return_value.open.side_effect = FileNotFoundError()
            result = _detect_total_mem_mb()
            assert result is None

    def test_detect_mem_from_proc(self) -> None:
        """Test memory detection from /proc/meminfo."""
        meminfo_content = "MemTotal:       16384000 kB\nMemFree:        8000000 kB"
        with (
            patch("python_pkg.stockfish_analysis.analyze_chess_game.psutil", None),
            patch("pathlib.Path.open", mock_open(read_data=meminfo_content)),
        ):
            result = _detect_total_mem_mb()
            assert result == 16000  # 16384000 kB / 1024

    def test_detect_mem_no_psutil_no_proc(self) -> None:
        """Test memory detection when both methods fail."""
        with (
            patch("python_pkg.stockfish_analysis.analyze_chess_game.psutil", None),
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
        ):
            result = _detect_total_mem_mb()
            assert result is None

    def test_detect_mem_proc_no_memtotal(self) -> None:
        """Test memory detection when MemTotal line is missing."""
        meminfo_content = "MemFree:        8000000 kB\nBuffers:        1000 kB"
        with (
            patch("python_pkg.stockfish_analysis.analyze_chess_game.psutil", None),
            patch("pathlib.Path.open", mock_open(read_data=meminfo_content)),
        ):
            result = _detect_total_mem_mb()
            assert result is None

    def test_detect_mem_proc_invalid_parts(self) -> None:
        """Test memory detection when MemTotal line has invalid format."""
        meminfo_content = "MemTotal: notanumber kB\nMemFree: 8000000 kB"
        with (
            patch("python_pkg.stockfish_analysis.analyze_chess_game.psutil", None),
            patch("pathlib.Path.open", mock_open(read_data=meminfo_content)),
        ):
            result = _detect_total_mem_mb()
            assert result is None

    def test_detect_mem_proc_short_parts(self) -> None:
        """Test memory detection when MemTotal has too few parts."""
        meminfo_content = "MemTotal:\nMemFree: 8000000 kB"
        with (
            patch("python_pkg.stockfish_analysis.analyze_chess_game.psutil", None),
            patch("pathlib.Path.open", mock_open(read_data=meminfo_content)),
        ):
            result = _detect_total_mem_mb()
            assert result is None


class TestAutoHashMb:
    """Tests for _auto_hash_mb function."""

    def test_auto_hash_basic(self) -> None:
        """Test basic auto hash calculation."""
        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._detect_total_mem_mb",
            return_value=8192,
        ):
            result = _auto_hash_mb(4, {})
            assert result >= 64
            assert result <= 4096

    def test_auto_hash_high_threads(self) -> None:
        """Test auto hash with high thread count."""
        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._detect_total_mem_mb",
            return_value=16384,
        ):
            result = _auto_hash_mb(20, {})
            assert result > 64

    def test_auto_hash_respects_engine_max(self) -> None:
        """Test auto hash respects engine maximum."""
        mock_opt = MagicMock()
        mock_opt.max = 256
        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._detect_total_mem_mb",
            return_value=8192,
        ):
            result = _auto_hash_mb(4, {"Hash": mock_opt})
            assert result <= 256

    def test_auto_hash_no_mem_info(self) -> None:
        """Test auto hash when memory detection fails."""
        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._detect_total_mem_mb",
            return_value=None,
        ):
            result = _auto_hash_mb(4, {})
            assert result >= 64

    def test_auto_hash_attribute_error(self) -> None:
        """Test auto hash when opt.max raises AttributeError."""

        class NoMaxOpt:
            """Object without max attribute."""

            @property
            def max(self) -> int:
                raise AttributeError

        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._detect_total_mem_mb",
            return_value=8192,
        ):
            result = _auto_hash_mb(4, {"Hash": NoMaxOpt()})
            assert result >= 64

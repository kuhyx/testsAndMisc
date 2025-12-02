"""Tests for analyze_chess_game module."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, mock_open, patch

import chess
import chess.engine
import chess.pgn
import pytest

from python_pkg.stockfish_analysis.analyze_chess_game import (
    AnalysisContext,
    MoveAnalysis,
    _analyze_all_moves,
    _analyze_last_move,
    _analyze_single_move,
    _auto_hash_mb,
    _build_argument_parser,
    _classify_mate_move,
    _configure_hash,
    _configure_multipv,
    _configure_nnue,
    _configure_threads,
    _detect_total_mem_mb,
    _evaluate_position,
    _get_best_move,
    _load_game,
    _log_engine_config,
    _log_move_analysis,
    _parse_hash_mb,
    _parse_threads,
    _run_analysis,
    _setup_engine,
    classify_cp_loss,
    extract_pgn_text,
    fmt_eval,
    main,
    score_to_cp,
)

if TYPE_CHECKING:
    from pathlib import Path


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


class TestConfigureThreads:
    """Tests for _configure_threads function."""

    def test_configure_threads_no_option(self) -> None:
        """Test thread config when engine has no Threads option."""
        engine = MagicMock()
        result = _configure_threads(engine, {}, 4)
        assert result == 4

    def test_configure_threads_with_limits(self) -> None:
        """Test thread config respects engine limits."""
        engine = MagicMock()
        mock_opt = MagicMock()
        mock_opt.max = 8
        mock_opt.min = 1
        result = _configure_threads(engine, {"Threads": mock_opt}, 16)
        assert result == 8
        engine.configure.assert_called_once()

    def test_configure_threads_auto(self) -> None:
        """Test thread config with auto detection."""
        engine = MagicMock()
        with patch("multiprocessing.cpu_count", return_value=8):
            result = _configure_threads(engine, {}, None)
            assert result == 8

    def test_configure_threads_exception(self) -> None:
        """Test thread config handles exceptions."""
        engine = MagicMock()
        engine.configure.side_effect = ValueError("Failed")
        mock_opt = MagicMock()
        mock_opt.max = 8
        mock_opt.min = 1
        # Should not raise, just log debug
        result = _configure_threads(engine, {"Threads": mock_opt}, 4)
        assert result == 4

    def test_configure_threads_no_max_min(self) -> None:
        """Test thread config when max/min are not integers."""
        engine = MagicMock()
        mock_opt = MagicMock()
        mock_opt.max = None
        mock_opt.min = None
        result = _configure_threads(engine, {"Threads": mock_opt}, 4)
        assert result == 4


class TestConfigureHash:
    """Tests for _configure_hash function."""

    def test_configure_hash_no_option(self) -> None:
        """Test hash config when engine has no Hash option."""
        engine = MagicMock()
        _configure_hash(engine, {}, 512, 4)
        engine.configure.assert_not_called()

    def test_configure_hash_with_limits(self) -> None:
        """Test hash config respects engine limits."""
        engine = MagicMock()
        mock_opt = MagicMock()
        mock_opt.max = 1024
        mock_opt.min = 16
        _configure_hash(engine, {"Hash": mock_opt}, 2048, 4)
        engine.configure.assert_called_once()

    def test_configure_hash_exception(self) -> None:
        """Test hash config handles exceptions."""
        engine = MagicMock()
        engine.configure.side_effect = TypeError("Failed")
        mock_opt = MagicMock()
        mock_opt.max = 1024
        mock_opt.min = 16
        # Should not raise, just log debug
        _configure_hash(engine, {"Hash": mock_opt}, 512, 4)

    def test_configure_hash_no_max_min(self) -> None:
        """Test hash config when max/min are not integers."""
        engine = MagicMock()
        mock_opt = MagicMock()
        mock_opt.max = None
        mock_opt.min = None
        _configure_hash(engine, {"Hash": mock_opt}, 512, 4)
        engine.configure.assert_called_once()


class TestConfigureMultipv:
    """Tests for _configure_multipv function."""

    def test_configure_multipv_no_option(self) -> None:
        """Test MultiPV config when engine has no option."""
        engine = MagicMock()
        result = _configure_multipv(engine, {}, 3)
        assert result == 3

    def test_configure_multipv_with_limit(self) -> None:
        """Test MultiPV config respects engine limit."""
        engine = MagicMock()
        mock_opt = MagicMock()
        mock_opt.max = 2
        result = _configure_multipv(engine, {"MultiPV": mock_opt}, 5)
        assert result == 2

    def test_configure_multipv_exception(self) -> None:
        """Test MultiPV config handles exceptions."""
        engine = MagicMock()
        engine.configure.side_effect = ValueError("Failed")
        mock_opt = MagicMock()
        mock_opt.max = 5
        # Should not raise, just log debug
        result = _configure_multipv(engine, {"MultiPV": mock_opt}, 3)
        assert result == 3

    def test_configure_multipv_no_max(self) -> None:
        """Test MultiPV config when max is not integer."""
        engine = MagicMock()
        mock_opt = MagicMock()
        mock_opt.max = None
        result = _configure_multipv(engine, {"MultiPV": mock_opt}, 3)
        assert result == 3
        engine.configure.assert_called_once()


class TestConfigureNnue:
    """Tests for _configure_nnue function."""

    def test_configure_nnue_use_nnue(self) -> None:
        """Test NNUE config with 'Use NNUE' option."""
        engine = MagicMock()
        _configure_nnue(engine, {"Use NNUE": MagicMock()})
        engine.configure.assert_called_once_with({"Use NNUE": True})

    def test_configure_nnue_usennue(self) -> None:
        """Test NNUE config with 'UseNNUE' option."""
        engine = MagicMock()
        _configure_nnue(engine, {"UseNNUE": MagicMock()})
        engine.configure.assert_called_once_with({"UseNNUE": True})

    def test_configure_nnue_not_supported(self) -> None:
        """Test NNUE config when not supported."""
        engine = MagicMock()
        _configure_nnue(engine, {})
        engine.configure.assert_not_called()


class TestBuildArgumentParser:
    """Tests for _build_argument_parser function."""

    def test_parser_required_args(self) -> None:
        """Test parser with required arguments."""
        parser = _build_argument_parser()
        args = parser.parse_args(["test.pgn"])
        assert args.file == "test.pgn"

    def test_parser_optional_args(self) -> None:
        """Test parser with optional arguments."""
        parser = _build_argument_parser()
        args = parser.parse_args(
            [
                "test.pgn",
                "--engine",
                "sf",
                "--time",
                "1.0",
                "--depth",
                "20",
                "--multipv",
                "3",
                "--last-move-only",
            ]
        )
        assert args.engine == "sf"
        assert args.time == 1.0
        assert args.depth == 20
        assert args.multipv == 3
        assert args.last_move_only is True


class TestLoadGame:
    """Tests for _load_game function."""

    def test_load_game_file_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent file."""
        with pytest.raises(SystemExit) as exc:
            _load_game(str(tmp_path / "nonexistent.pgn"))
        assert exc.value.code == 1

    def test_load_game_no_pgn(self, tmp_path: Path) -> None:
        """Test loading file with no PGN content."""
        pgn_file = tmp_path / "empty.pgn"
        pgn_file.write_text("No PGN here")
        with pytest.raises(SystemExit) as exc:
            _load_game(str(pgn_file))
        assert exc.value.code == 2

    def test_load_game_success(self, tmp_path: Path) -> None:
        """Test successful game loading."""
        pgn_file = tmp_path / "game.pgn"
        pgn_file.write_text('[Event "Test"]\n\n1. e4 e5 2. Nf3 *')
        game = _load_game(str(pgn_file))
        assert game is not None

    def test_load_game_invalid_pgn(self, tmp_path: Path) -> None:
        """Test loading file when read_game returns None."""
        pgn_file = tmp_path / "invalid.pgn"
        pgn_file.write_text('[Event "Test"]\n\n1. e4 *')
        # Mock read_game to return None to trigger exit code 3
        with (
            patch("chess.pgn.read_game", return_value=None),
            pytest.raises(SystemExit) as exc,
        ):
            _load_game(str(pgn_file))
        assert exc.value.code == 3


class TestSetupEngine:
    """Tests for _setup_engine function."""

    def test_setup_engine_not_found(self) -> None:
        """Test engine setup with non-existent engine."""
        args = argparse.Namespace(
            engine="nonexistent_engine",
            time=0.5,
            depth=None,
            threads=None,
            hash_mb=None,
            multipv=2,
        )
        with pytest.raises(SystemExit) as exc:
            _setup_engine(args)
        assert exc.value.code == 4

    def test_setup_engine_with_depth(self) -> None:
        """Test engine setup with depth limit."""
        mock_engine = MagicMock()
        mock_engine.options = {}

        args = argparse.Namespace(
            engine="stockfish",
            time=0.5,
            depth=20,
            threads=4,
            hash_mb=512,
            multipv=2,
        )

        with patch("chess.engine.SimpleEngine.popen_uci", return_value=mock_engine):
            engine, _mpv, limit = _setup_engine(args)
            assert engine == mock_engine
            assert limit.depth == 20

    def test_setup_engine_with_time(self) -> None:
        """Test engine setup with time limit."""
        mock_engine = MagicMock()
        mock_engine.options = {}

        args = argparse.Namespace(
            engine="stockfish",
            time=1.0,
            depth=None,
            threads=None,
            hash_mb=None,
            multipv=2,
        )

        with patch("chess.engine.SimpleEngine.popen_uci", return_value=mock_engine):
            _engine, _mpv, limit = _setup_engine(args)
            assert limit.time == 1.0

    def test_setup_engine_options_attr_error(self) -> None:
        """Test engine setup when options raises AttributeError."""
        from unittest.mock import PropertyMock

        mock_engine = MagicMock()
        # Delete the auto-created options attribute first
        del mock_engine.options
        # Then set up PropertyMock to raise AttributeError
        type(mock_engine).options = PropertyMock(side_effect=AttributeError)

        args = argparse.Namespace(
            engine="stockfish",
            time=1.0,
            depth=None,
            threads=None,
            hash_mb=None,
            multipv=2,
        )

        with patch("chess.engine.SimpleEngine.popen_uci", return_value=mock_engine):
            engine, _mpv, limit = _setup_engine(args)
            assert engine == mock_engine
            assert limit.time == 1.0


class TestLogEngineConfig:
    """Tests for _log_engine_config function."""

    def test_log_with_hash(self) -> None:
        """Test logging config with hash value."""
        mock_engine = MagicMock()
        mock_hash = MagicMock()
        mock_hash.value = 512
        mock_engine.options.get.return_value = mock_hash

        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._logger"
        ) as mock_logger:
            _log_engine_config(mock_engine, 4, 2)
            mock_logger.info.assert_called()

    def test_log_without_hash(self) -> None:
        """Test logging config without hash value."""
        mock_engine = MagicMock()
        mock_engine.options.get.return_value = None

        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._logger"
        ) as mock_logger:
            _log_engine_config(mock_engine, 4, 2)
            mock_logger.info.assert_called()

    def test_log_with_hash_exception(self) -> None:
        """Test logging config when hash access raises exception."""
        from unittest.mock import PropertyMock

        mock_engine = MagicMock()
        # Make .value access raise
        mock_hash = MagicMock()
        type(mock_hash).value = PropertyMock(side_effect=TypeError)
        mock_engine.options.get.return_value = mock_hash

        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._logger"
        ) as mock_logger:
            _log_engine_config(mock_engine, 4, 2)
            # Should still call info (without hash)
            mock_logger.info.assert_called()


class TestGetBestMove:
    """Tests for _get_best_move function."""

    def test_get_best_move_from_analysis(self) -> None:
        """Test getting best move from analysis."""
        mock_engine = MagicMock()
        mock_move = chess.Move.from_uci("e2e4")
        mock_engine.analyse.return_value = [{"pv": [mock_move]}]

        board = chess.Board()
        limit = chess.engine.Limit(time=0.1)

        result = _get_best_move(mock_engine, board, limit, 2)
        assert result == mock_move

    def test_get_best_move_fallback_to_play(self) -> None:
        """Test getting best move via play when analysis fails."""
        mock_engine = MagicMock()
        mock_engine.analyse.return_value = [{}]
        mock_move = chess.Move.from_uci("e2e4")
        mock_engine.play.return_value = MagicMock(move=mock_move)

        board = chess.Board()
        limit = chess.engine.Limit(time=0.1)

        result = _get_best_move(mock_engine, board, limit, 2)
        assert result == mock_move


class TestEvaluatePosition:
    """Tests for _evaluate_position function."""

    def test_evaluate_position_success(self) -> None:
        """Test successful position evaluation."""
        mock_engine = MagicMock()
        mock_score = MagicMock()
        mock_pov = MagicMock()
        mock_pov.is_mate.return_value = False
        mock_pov.score.return_value = 50
        mock_score.pov.return_value = mock_pov
        mock_engine.analyse.return_value = [{"score": mock_score}]

        board = chess.Board()
        limit = chess.engine.Limit(time=0.1)

        cp, mate = _evaluate_position(mock_engine, board, limit, 2, pov_white=True)
        assert cp == 50
        assert mate is None

    def test_evaluate_position_no_score(self) -> None:
        """Test evaluation with no score."""
        mock_engine = MagicMock()
        mock_engine.analyse.return_value = [{}]

        board = chess.Board()
        limit = chess.engine.Limit(time=0.1)

        cp, mate = _evaluate_position(mock_engine, board, limit, 2, pov_white=True)
        assert cp is None
        assert mate is None


class TestClassifyMateMove:
    """Tests for _classify_mate_move function."""

    def test_classify_mate_missing_values(self) -> None:
        """Test classification with missing mate values."""
        assert _classify_mate_move(None, 2) == "Blunder"
        assert _classify_mate_move(2, None) == "Blunder"

    def test_classify_mate_both_positive(self) -> None:
        """Test classification with both positive mates."""
        assert _classify_mate_move(2, 3) == "Inaccuracy"
        assert _classify_mate_move(3, 3) == "Best"
        assert _classify_mate_move(3, 2) == "Best"

    def test_classify_mate_both_negative(self) -> None:
        """Test classification with both negative mates."""
        assert _classify_mate_move(-3, -2) == "Blunder"
        assert _classify_mate_move(-2, -2) == "Best"
        assert _classify_mate_move(-2, -3) == "Good"

    def test_classify_mate_opposite_signs(self) -> None:
        """Test classification with opposite sign mates."""
        assert _classify_mate_move(2, -2) == "Blunder"
        assert _classify_mate_move(-2, 2) == "Blunder"


class TestAnalyzeSingleMove:
    """Tests for _analyze_single_move function."""

    def test_analyze_single_move(self) -> None:
        """Test analyzing a single move."""
        mock_engine = MagicMock()

        # Mock best move
        best_move = chess.Move.from_uci("e2e4")
        mock_engine.analyse.return_value = [{"pv": [best_move]}]

        # Mock score
        mock_score = MagicMock()
        mock_pov = MagicMock()
        mock_pov.is_mate.return_value = False
        mock_pov.score.return_value = 30
        mock_score.pov.return_value = mock_pov

        mock_engine.analyse.return_value = [{"pv": [best_move], "score": mock_score}]

        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        result = _analyze_single_move(ctx, board, move)
        assert isinstance(result, MoveAnalysis)
        assert result.san == "e4"

    def test_analyze_single_move_no_best_move(self) -> None:
        """Test analyzing when engine returns no best move."""
        mock_engine = MagicMock()

        # Mock engine returning no pv
        mock_engine.analyse.return_value = [{}]
        mock_engine.play.return_value = MagicMock(move=None)

        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        result = _analyze_single_move(ctx, board, move)
        assert isinstance(result, MoveAnalysis)
        assert result.best_san == "?"

    def test_analyze_single_move_with_mate(self) -> None:
        """Test analyzing a move with mate score."""
        mock_engine = MagicMock()

        best_move = chess.Move.from_uci("e2e4")

        def mock_analyse(
            _board: chess.Board, **_kwargs: object
        ) -> list[dict[str, object]]:
            mock_score = MagicMock()
            mock_pov = MagicMock()
            mock_pov.is_mate.return_value = True
            mock_pov.mate.return_value = 3
            mock_score.pov.return_value = mock_pov
            return [{"pv": [best_move], "score": mock_score}]

        mock_engine.analyse.side_effect = mock_analyse

        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        result = _analyze_single_move(ctx, board, move)
        assert isinstance(result, MoveAnalysis)

    def test_analyze_single_move_unknown_classification(self) -> None:
        """Test analyzing when both cp and mate are None."""
        mock_engine = MagicMock()

        best_move = chess.Move.from_uci("e2e4")

        def mock_analyse(
            _board: chess.Board, **_kwargs: object
        ) -> list[dict[str, object]]:
            mock_score = MagicMock()
            mock_pov = MagicMock()
            mock_pov.is_mate.return_value = False
            mock_pov.score.return_value = None
            mock_score.pov.return_value = mock_pov
            return [{"pv": [best_move], "score": mock_score}]

        mock_engine.analyse.side_effect = mock_analyse

        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        result = _analyze_single_move(ctx, board, move)
        assert result.classification == "Unknown"


class TestLogMoveAnalysis:
    """Tests for _log_move_analysis function."""

    def test_log_move_analysis(self) -> None:
        """Test logging move analysis."""
        result = MoveAnalysis(
            san="e4",
            best_san="e4",
            played_cp=30,
            played_mate=None,
            best_cp=30,
            best_mate=None,
            cp_loss=0,
            classification="Best",
        )

        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._logger"
        ) as mock_logger:
            _log_move_analysis(1, result, mover_white=True)
            mock_logger.info.assert_called()


class TestRunAnalysis:
    """Tests for _run_analysis function."""

    def test_run_analysis_all_moves(self) -> None:
        """Test running analysis on all moves."""
        mock_engine = MagicMock()

        def mock_analyse(
            board: chess.Board, **_kwargs: object
        ) -> list[dict[str, object]]:
            """Return a legal move for the given position."""
            legal_moves = list(board.legal_moves)
            mock_score = MagicMock()
            mock_pov = MagicMock()
            mock_pov.is_mate.return_value = False
            mock_pov.score.return_value = 30
            mock_score.pov.return_value = mock_pov
            pv = [legal_moves[0]] if legal_moves else []
            return [{"pv": pv, "score": mock_score}]

        mock_engine.analyse.side_effect = mock_analyse

        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )

        game = chess.pgn.Game()
        node = game.add_variation(chess.Move.from_uci("e2e4"))
        node.add_variation(chess.Move.from_uci("e7e5"))

        _run_analysis(game, ctx, last_move_only=False)


class TestAnalyzeLastMove:
    """Tests for _analyze_last_move function."""

    def test_analyze_last_move_no_moves(self) -> None:
        """Test analyzing last move with no moves."""
        mock_engine = MagicMock()
        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )

        game = chess.pgn.Game()
        board = game.board()

        with patch(
            "python_pkg.stockfish_analysis.analyze_chess_game._logger"
        ) as mock_logger:
            _analyze_last_move(game, board, ctx)
            mock_logger.warning.assert_called_once()

    def test_analyze_last_move_with_moves(self) -> None:
        """Test analyzing last move with actual moves."""
        mock_engine = MagicMock()

        def mock_analyse(
            board: chess.Board, **_kwargs: object
        ) -> list[dict[str, object]]:
            """Return a legal move for the given position."""
            legal_moves = list(board.legal_moves)
            mock_score = MagicMock()
            mock_pov = MagicMock()
            mock_pov.is_mate.return_value = False
            mock_pov.score.return_value = 30
            mock_score.pov.return_value = mock_pov
            pv = [legal_moves[0]] if legal_moves else []
            return [{"pv": pv, "score": mock_score}]

        mock_engine.analyse.side_effect = mock_analyse

        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )

        game = chess.pgn.Game()
        node = game.add_variation(chess.Move.from_uci("e2e4"))
        node.add_variation(chess.Move.from_uci("e7e5"))
        board = game.board()

        _analyze_last_move(game, board, ctx)


class TestAnalyzeAllMoves:
    """Tests for _analyze_all_moves function."""

    def test_analyze_all_moves(self) -> None:
        """Test analyzing all moves."""
        mock_engine = MagicMock()
        mock_move = chess.Move.from_uci("e2e4")
        mock_score = MagicMock()
        mock_pov = MagicMock()
        mock_pov.is_mate.return_value = False
        mock_pov.score.return_value = 30
        mock_score.pov.return_value = mock_pov
        mock_engine.analyse.return_value = [{"pv": [mock_move], "score": mock_score}]

        ctx = AnalysisContext(
            engine=mock_engine,
            limit=chess.engine.Limit(time=0.1),
            multipv=2,
        )

        game = chess.pgn.Game()
        game.add_variation(chess.Move.from_uci("e2e4"))
        board = game.board()

        _analyze_all_moves(game, board, ctx)


class TestMain:
    """Tests for main function."""

    def test_main(self, tmp_path: Path) -> None:
        """Test main function."""
        pgn_file = tmp_path / "game.pgn"
        pgn_file.write_text('[Event "Test"]\n\n1. e4 *')

        mock_engine = MagicMock()
        mock_move = chess.Move.from_uci("e2e4")
        mock_score = MagicMock()
        mock_pov = MagicMock()
        mock_pov.is_mate.return_value = False
        mock_pov.score.return_value = 30
        mock_score.pov.return_value = mock_pov
        mock_engine.analyse.return_value = [{"pv": [mock_move], "score": mock_score}]
        mock_engine.options = {}

        with (
            patch("sys.argv", ["prog", str(pgn_file)]),
            patch(
                "chess.engine.SimpleEngine.popen_uci",
                return_value=mock_engine,
            ),
        ):
            main()
            mock_engine.quit.assert_called_once()

    def test_main_last_move_only(self, tmp_path: Path) -> None:
        """Test main function with --last-move-only flag."""
        pgn_file = tmp_path / "game.pgn"
        pgn_file.write_text('[Event "Test"]\n\n1. e4 e5 2. Nf3 *')

        mock_engine = MagicMock()

        def mock_analyse(
            board: chess.Board, **_kwargs: object
        ) -> list[dict[str, object]]:
            legal_moves = list(board.legal_moves)
            mock_score = MagicMock()
            mock_pov = MagicMock()
            mock_pov.is_mate.return_value = False
            mock_pov.score.return_value = 30
            mock_score.pov.return_value = mock_pov
            pv = [legal_moves[0]] if legal_moves else []
            return [{"pv": pv, "score": mock_score}]

        mock_engine.analyse.side_effect = mock_analyse
        mock_engine.options = {}

        with (
            patch("sys.argv", ["prog", str(pgn_file), "--last-move-only"]),
            patch(
                "chess.engine.SimpleEngine.popen_uci",
                return_value=mock_engine,
            ),
        ):
            main()
            mock_engine.quit.assert_called_once()

    def test_main_with_engine_options_attr_error(self, tmp_path: Path) -> None:
        """Test main when engine.options raises AttributeError."""
        pgn_file = tmp_path / "game.pgn"
        pgn_file.write_text('[Event "Test"]\n\n1. e4 *')

        mock_engine = MagicMock()
        mock_move = chess.Move.from_uci("e2e4")
        mock_score = MagicMock()
        mock_pov = MagicMock()
        mock_pov.is_mate.return_value = False
        mock_pov.score.return_value = 30
        mock_score.pov.return_value = mock_pov
        mock_engine.analyse.return_value = [{"pv": [mock_move], "score": mock_score}]

        # Delete auto-created options, then set up PropertyMock to raise
        from unittest.mock import PropertyMock

        del mock_engine.options
        type(mock_engine).options = PropertyMock(side_effect=AttributeError)

        with (
            patch("sys.argv", ["prog", str(pgn_file)]),
            patch(
                "chess.engine.SimpleEngine.popen_uci",
                return_value=mock_engine,
            ),
        ):
            main()
            mock_engine.quit.assert_called_once()

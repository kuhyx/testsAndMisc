"""Tests for analyze_chess_game configuration functions."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from python_pkg.stockfish_analysis.analyze_chess_game import (
    _build_argument_parser,
    _configure_hash,
    _configure_multipv,
    _configure_nnue,
    _configure_threads,
    _load_game,
    _log_engine_config,
    _setup_engine,
)

if TYPE_CHECKING:
    from pathlib import Path


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
        engine.configure.assert_not_called()


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

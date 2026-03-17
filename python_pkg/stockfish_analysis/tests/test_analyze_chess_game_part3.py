"""Tests for analyze_chess_game analysis and main functions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, patch

import chess
import chess.engine
import chess.pgn

from python_pkg.stockfish_analysis.analyze_chess_game import (
    AnalysisContext,
    MoveAnalysis,
    _analyze_all_moves,
    _analyze_last_move,
    _analyze_single_move,
    _classify_mate_move,
    _evaluate_position,
    _get_best_move,
    _log_move_analysis,
    _run_analysis,
    main,
)

if TYPE_CHECKING:
    from pathlib import Path


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

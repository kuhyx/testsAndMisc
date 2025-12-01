"""Unit tests for lichess_bot engine module."""

# ruff: noqa: SLF001
# Tests need to access private members to verify internal logic

import json
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

import chess
import pytest

from python_pkg.lichess_bot.engine import RandomEngine


class TestRandomEngineInit:
    """Tests for RandomEngine initialization."""

    def test_init_with_missing_engine_raises(self) -> None:
        """Test that missing engine raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="C engine not found"):
            RandomEngine(engine_path="/nonexistent/path/to/engine")

    def test_init_with_non_executable_raises(self, tmp_path: Path) -> None:
        """Test that non-executable engine raises FileNotFoundError."""
        fake_engine = tmp_path / "fake_engine"
        fake_engine.write_text("not executable")
        with pytest.raises(FileNotFoundError, match="not executable"):
            RandomEngine(engine_path=str(fake_engine))

    def test_init_with_valid_engine(self, tmp_path: Path) -> None:
        """Test successful initialization with valid engine."""
        fake_engine = tmp_path / "fake_engine"
        fake_engine.write_text("#!/bin/bash\necho test")
        fake_engine.chmod(0o755)

        engine = RandomEngine(engine_path=str(fake_engine), max_time_sec=1.0, depth=5)

        assert engine.engine_path == fake_engine
        assert engine.max_time_sec == 1.0
        assert engine.depth == 5


class TestCallEngine:
    """Tests for _call_engine method."""

    @pytest.fixture
    def mock_engine(self, tmp_path: Path) -> RandomEngine:
        """Create an engine with a mock executable."""
        fake_engine = tmp_path / "fake_engine"
        fake_engine.write_text("#!/bin/bash\necho test")
        fake_engine.chmod(0o755)
        return RandomEngine(engine_path=str(fake_engine))

    def test_call_engine_success(self, mock_engine: RandomEngine) -> None:
        """Test successful engine call."""
        mock_result = MagicMock()
        mock_result.stdout = "e2e4\n"

        with patch("subprocess.run", return_value=mock_result):
            result = mock_engine._call_engine(["--test"], timeout=1.0)

        assert result == "e2e4"

    def test_call_engine_called_process_error(self, mock_engine: RandomEngine) -> None:
        """Test engine call with CalledProcessError."""
        error = subprocess.CalledProcessError(1, "cmd", stderr="engine error")

        with (
            patch("subprocess.run", side_effect=error),
            pytest.raises(RuntimeError, match="C engine failed"),
        ):
            mock_engine._call_engine(["--test"], timeout=1.0)

    def test_call_engine_timeout(self, mock_engine: RandomEngine) -> None:
        """Test engine call timeout."""
        error = subprocess.TimeoutExpired("cmd", 1.0)

        with (
            patch("subprocess.run", side_effect=error),
            pytest.raises(TimeoutError, match="C engine timed out"),
        ):
            mock_engine._call_engine(["--test"], timeout=1.0)


class TestChooseMove:
    """Tests for choose_move methods."""

    @pytest.fixture
    def mock_engine(self, tmp_path: Path) -> RandomEngine:
        """Create an engine with a mock executable."""
        fake_engine = tmp_path / "fake_engine"
        fake_engine.write_text("#!/bin/bash\necho test")
        fake_engine.chmod(0o755)
        return RandomEngine(engine_path=str(fake_engine))

    def test_choose_move_returns_valid_move(self, mock_engine: RandomEngine) -> None:
        """Test choose_move returns a valid move."""
        board = chess.Board()

        with patch.object(mock_engine, "_call_engine", return_value="e2e4"):
            move = mock_engine.choose_move(board)

        assert move == chess.Move.from_uci("e2e4")
        assert move in board.legal_moves

    def test_choose_move_with_explanation_no_legal_moves(
        self, mock_engine: RandomEngine
    ) -> None:
        """Test choose_move_with_explanation when no legal moves."""
        # Create a checkmate position - black king checkmated by rook
        board = chess.Board("k7/2K5/8/8/8/8/8/R7 b - - 0 1")

        move, reason = mock_engine.choose_move_with_explanation(
            board, time_budget_sec=1.0
        )

        assert move is None
        assert reason == "no_legal_moves"

    def test_choose_move_with_explanation_invalid_move(
        self, mock_engine: RandomEngine
    ) -> None:
        """Test choose_move_with_explanation with invalid move from engine."""
        board = chess.Board()

        with (
            patch.object(mock_engine, "_call_engine", return_value="invalid"),
            pytest.raises(RuntimeError, match="Engine returned invalid move"),
        ):
            mock_engine.choose_move_with_explanation(board, time_budget_sec=1.0)

    def test_choose_move_with_explanation_illegal_move(
        self, mock_engine: RandomEngine
    ) -> None:
        """Test choose_move_with_explanation with illegal move from engine."""
        board = chess.Board()

        # e2e5 is a valid UCI format but illegal from starting position
        with (
            patch.object(mock_engine, "_call_engine", return_value="e2e5"),
            pytest.raises(RuntimeError, match="Engine returned illegal move"),
        ):
            mock_engine.choose_move_with_explanation(board, time_budget_sec=1.0)


class TestParseEngineAnalysis:
    """Tests for _parse_engine_analysis method."""

    @pytest.fixture
    def mock_engine(self, tmp_path: Path) -> RandomEngine:
        """Create an engine with a mock executable."""
        fake_engine = tmp_path / "fake_engine"
        fake_engine.write_text("#!/bin/bash\necho test")
        fake_engine.chmod(0o755)
        return RandomEngine(engine_path=str(fake_engine))

    def test_parse_valid_json(self, mock_engine: RandomEngine) -> None:
        """Test parsing valid JSON output."""
        board = chess.Board()
        legal_moves = list(board.legal_moves)
        output = json.dumps(
            {
                "analyze": {"candidate_score": 0.5},
                "chosen_move": "e2e4",
                "chosen_index": 0,
            }
        )

        score, cand_expl, best_move, best_expl = mock_engine._parse_engine_analysis(
            output, legal_moves
        )

        assert score == 0.5
        assert best_move == chess.Move.from_uci("e2e4")
        assert "candidate_score" in cand_expl
        assert "chosen_move" in best_expl

    def test_parse_invalid_json(self, mock_engine: RandomEngine) -> None:
        """Test parsing invalid JSON output."""
        board = chess.Board()
        legal_moves = list(board.legal_moves)

        score, cand_expl, best_move, _best_expl = mock_engine._parse_engine_analysis(
            "not json", legal_moves
        )

        assert score == 0.0
        assert best_move is None
        assert cand_expl == "not json"

    def test_parse_json_with_illegal_move(self, mock_engine: RandomEngine) -> None:
        """Test parsing JSON with illegal move."""
        legal_moves = [chess.Move.from_uci("e2e4")]
        output = json.dumps(
            {
                "analyze": {"candidate_score": 1.0},
                "chosen_move": "a1a8",  # Not in legal moves
                "chosen_index": 0,
            }
        )

        score, _cand_expl, best_move, _best_expl = mock_engine._parse_engine_analysis(
            output, legal_moves
        )

        assert score == 1.0
        assert best_move is None  # Move not in legal moves

    def test_parse_json_without_chosen_move(self, mock_engine: RandomEngine) -> None:
        """Test parsing JSON without chosen_move field."""
        legal_moves = [chess.Move.from_uci("e2e4")]
        output = json.dumps(
            {
                "analyze": {"candidate_score": 0.7},
                "chosen_index": 0,
                # No chosen_move field
            }
        )

        score, _cand_expl, best_move, _best_expl = mock_engine._parse_engine_analysis(
            output, legal_moves
        )

        assert score == 0.7
        assert best_move is None

    def test_parse_json_without_score(self, mock_engine: RandomEngine) -> None:
        """Test parsing JSON without candidate_score field."""
        board = chess.Board()
        legal_moves = list(board.legal_moves)
        output = json.dumps(
            {
                "analyze": {},  # No candidate_score
                "chosen_move": "e2e4",
                "chosen_index": 0,
            }
        )

        score, _cand_expl, best_move, _best_expl = mock_engine._parse_engine_analysis(
            output, legal_moves
        )

        assert score == 0.0  # Default score
        assert best_move == chess.Move.from_uci("e2e4")


class TestEvaluateProposedMove:
    """Tests for evaluate_proposed_move_with_suggestion method."""

    @pytest.fixture
    def mock_engine(self, tmp_path: Path) -> RandomEngine:
        """Create an engine with a mock executable."""
        fake_engine = tmp_path / "fake_engine"
        fake_engine.write_text("#!/bin/bash\necho test")
        fake_engine.chmod(0o755)
        return RandomEngine(engine_path=str(fake_engine))

    def test_evaluate_no_legal_moves(self, mock_engine: RandomEngine) -> None:
        """Test evaluate when no legal moves available."""
        # Create a checkmate position - black king checkmated by rook
        board = chess.Board("k7/2K5/8/8/8/8/8/R7 b - - 0 1")

        score, cand_expl, best_move, best_expl = (
            mock_engine.evaluate_proposed_move_with_suggestion(
                board, "e1e2", time_budget_sec=1.0
            )
        )

        assert score == 0.0
        assert cand_expl == "no_legal_moves"
        assert best_move is None
        assert best_expl == "no_best_move"

        assert score == 0.0
        assert cand_expl == "no_legal_moves"
        assert best_move is None
        assert best_expl == "no_best_move"

    def test_evaluate_with_valid_position(self, mock_engine: RandomEngine) -> None:
        """Test evaluate with a valid position."""
        board = chess.Board()
        output = json.dumps(
            {
                "analyze": {"candidate_score": 0.3},
                "chosen_move": "e2e4",
                "chosen_index": 0,
            }
        )

        with patch.object(mock_engine, "_call_engine", return_value=output):
            score, _cand_expl, best_move, _best_expl = (
                mock_engine.evaluate_proposed_move_with_suggestion(
                    board, "d2d4", time_budget_sec=1.0
                )
            )

        assert score == 0.3
        assert best_move == chess.Move.from_uci("e2e4")

#!/usr/bin/env python3
"""Analyze a chess game's moves using a local Stockfish engine and rate each move.

Usage:
    python3 python_pkg/analyze_chess_game.py <path-to-file>
        [--engine stockfish]
        [--time 0.5 | --depth 20]
        [--threads auto|N]
        [--hash-mb auto|MB]
        [--multipv N]
        [--last-move-only]

Notes:
    - Requires python-chess. Install from python_pkg/stockfish_analysis/requirements.txt
    - The input file can be a pure PGN or a log file containing a PGN section.
    - The script tries to locate the PGN by looking for a 'PGN:' marker,
      PGN tags '[...]', or a move list starting with '1.'.
    - Stockfish is CPU-based; it doesn't use GPU VRAM. "Full power" here means
      using many CPU threads and a large transposition table (Hash).
"""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass
import io
import logging
import multiprocessing
from pathlib import Path
import re
import sys

_logger = logging.getLogger(__name__)

try:
    import psutil  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

try:
    import chess
    import chess.engine
    import chess.pgn
except ImportError:  # pragma: no cover
    _logger.exception("Missing dependency. Please install python-chess:")
    _logger.exception("  pip install -r python_pkg/stockfish_analysis/requirements.txt")
    raise

# Memory configuration constants
MEMINFO_PARTS_MIN = 2
HIGH_THREAD_COUNT = 16


def extract_pgn_text(raw: str) -> str | None:
    """Try to extract a PGN block from a possibly noisy file.

    Strategies tried in order:
      1) Everything after a line that equals or starts with 'PGN:'
      2) From the first PGN tag line '[' to the end
      3) From the first line starting with an integer and a dot (e.g., '1.') to the end
    """
    lines = raw.splitlines()

    # 1) After 'PGN:' marker
    for i, line in enumerate(lines):
        if line.strip().startswith("PGN:"):
            # everything after this line
            pgn = "\n".join(lines[i + 1 :]).strip()
            if pgn:
                return pgn

    # 2) From first tag line
    for i, line in enumerate(lines):
        if line.strip().startswith("[") and "]" in line:
            pgn = "\n".join(lines[i:]).strip()
            if pgn:
                return pgn

    # 3) From first move number
    move_start_re = re.compile(r"^\s*\d+\.")
    for i, line in enumerate(lines):
        if move_start_re.match(line):
            pgn = "\n".join(lines[i:]).strip()
            if pgn:
                return pgn

    return None


def score_to_cp(
    score: chess.engine.PovScore, *, pov_white: bool
) -> tuple[int | None, int | None]:
    """Return tuple (cp, mate_in) from a PovScore for the given POV color.

    If it's a mate score, cp will be None and mate_in will be +/-N
    (positive means mate for POV side). If it's a cp score, mate_in will be None.
    """
    pov = chess.WHITE if pov_white else chess.BLACK
    s = score.pov(pov)
    if s.is_mate():
        mi = s.mate()
        return None, mi
    return s.score(mate_score=None), None


# Centipawn loss thresholds for move quality classification (Lichess-like bands)
CP_LOSS_BEST = 10
CP_LOSS_EXCELLENT = 20
CP_LOSS_GOOD = 50
CP_LOSS_INACCURACY = 99
CP_LOSS_MISTAKE = 299


# Centipawn loss thresholds for move classification
_CP_LOSS_BANDS = [
    (CP_LOSS_BEST, "Best"),
    (CP_LOSS_EXCELLENT, "Excellent"),
    (CP_LOSS_GOOD, "Good"),
    (CP_LOSS_INACCURACY, "Inaccuracy"),
    (CP_LOSS_MISTAKE, "Mistake"),
]


def classify_cp_loss(cp_loss: int | None) -> str:
    """Classify move quality using Lichess-like centipawn loss bands.

    Loss is best_eval(cp) - played_eval(cp), from the mover's POV (positive is worse).
    Bands (approx, widely cited):
      - Best:    0..10 cp
      - Excellent: 11..20 cp
      - Good:    21..50 cp
      - Inaccuracy: 51..99 cp
      - Mistake: 100..299 cp
      - Blunder: >=300 cp
    """
    if cp_loss is None:
        return "Unknown"
    for threshold, classification in _CP_LOSS_BANDS:
        if cp_loss <= threshold:
            return classification
    return "Blunder"


def fmt_eval(cp: int | None, mate_in: int | None) -> str:
    """Format evaluation score as human-readable string."""
    if mate_in is not None:
        sign = "+" if mate_in > 0 else ""
        return f"M{sign}{mate_in}"
    if cp is None:
        return "?"
    # Convert cp to pawns with sign and 2 decimals
    return f"{cp / 100.0:+.2f}"


def _parse_threads(value: str) -> int | None:
    v = value.strip().lower()
    if v in ("auto", "max", ""):  # auto-detect
        return None
    try:
        n = int(v)
        return max(1, n)
    except ValueError:
        msg = "--threads must be an integer or 'auto'"
        raise argparse.ArgumentTypeError(msg) from None


def _parse_hash_mb(value: str) -> int | None:
    v = value.strip().lower()
    if v in ("auto", "max", ""):  # auto-detect
        return None
    try:
        mb = int(v)
        return max(16, mb)
    except ValueError:
        msg = "--hash-mb must be an integer (MB) or 'auto'"
        raise argparse.ArgumentTypeError(msg) from None


def _detect_total_mem_mb() -> int | None:
    # Prefer psutil if available
    if psutil is not None:
        with contextlib.suppress(Exception):
            return int(psutil.virtual_memory().total // (1024 * 1024))
    # Fallback approach for Linux systems using proc meminfo.
    with (
        contextlib.suppress(Exception),
        Path("/proc/meminfo").open(encoding="utf-8", errors="ignore") as f,
    ):
        for line in f:
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= MEMINFO_PARTS_MIN and parts[1].isdigit():
                    # Value is in kB
                    kb = int(parts[1])
                    return kb // 1024
    return None


def _auto_hash_mb(threads_wanted: int, engine_options: dict[str, object]) -> int:
    total_mb = _detect_total_mem_mb() or 2048
    # Heuristic: cap at 4 GiB by default; keep at most half of RAM; ensure >= 64MB
    half_ram = max(64, total_mb // 2)
    target = half_ram
    # Respect engine "Hash" max if exposed
    opt = engine_options.get("Hash")
    max_allowed = None
    try:
        max_allowed = opt.max if opt is not None else None  # type: ignore[attr-defined]
    except AttributeError:
        max_allowed = None
    if isinstance(max_allowed, int):
        target = min(target, max_allowed)
    # Some rough scaling: if very many threads, give a bit more (but not huge)
    if threads_wanted >= HIGH_THREAD_COUNT:
        target = min(target + 1024, (total_mb * 3) // 4)
    return max(64, int(target))


# Type aliases for clarity
EngineOptions = dict[str, object]


@dataclass
class MoveAnalysis:
    """Container for single move analysis results."""

    san: str
    best_san: str
    played_cp: int | None
    played_mate: int | None
    best_cp: int | None
    best_mate: int | None
    cp_loss: int | None
    classification: str


@dataclass
class AnalysisContext:
    """Container for analysis parameters passed between functions."""

    engine: chess.engine.SimpleEngine
    limit: chess.engine.Limit
    multipv: int


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the analysis script."""
    ap = argparse.ArgumentParser(
        description="Analyze a chess game's moves with Stockfish and rate each move."
    )
    ap.add_argument("file", help="Path to a PGN file or a log containing a PGN section")
    ap.add_argument(
        "--engine",
        default="stockfish",
        help="Path to stockfish executable (default: stockfish)",
    )
    ap.add_argument(
        "--time",
        type=float,
        default=0.5,
        help="Analysis time per evaluation in seconds (default: 0.5)",
    )
    ap.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Fixed depth per evaluation (overrides --time)",
    )
    ap.add_argument(
        "--threads",
        type=_parse_threads,
        default=None,
        metavar="auto|N",
        help="Engine threads to use (default: auto = all logical cores)",
    )
    ap.add_argument(
        "--hash-mb",
        type=_parse_hash_mb,
        default=None,
        metavar="auto|MB",
        help="Hash table size in MB (default: auto = up to half RAM, capped)",
    )
    ap.add_argument(
        "--multipv",
        type=int,
        default=2,
        help="Number of principal variations to compute (default: 1)",
    )
    ap.add_argument(
        "--last-move-only",
        action="store_true",
        help=(
            "Analyze only the last move of the main line "
            "(reports its eval and the best move)"
        ),
    )
    return ap


def _load_game(file_path: str) -> chess.pgn.Game:
    """Load and parse a chess game from a file."""
    if not Path(file_path).is_file():
        _logger.error("Input not found: %s", file_path)
        sys.exit(1)

    with Path(file_path).open(encoding="utf-8", errors="replace") as f:
        raw = f.read()

    pgn_text = extract_pgn_text(raw)
    if not pgn_text:
        _logger.error("Could not locate PGN text in the file.")
        sys.exit(2)

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        _logger.error("Failed to parse PGN.")
        sys.exit(3)

    return game


def _configure_threads(
    engine: chess.engine.SimpleEngine,
    options: EngineOptions,
    requested: int | None,
) -> int:
    """Configure engine thread count and return actual threads used."""
    wanted = requested if requested is not None else (multiprocessing.cpu_count() or 1)
    if "Threads" not in options:
        return wanted
    try:
        max_thr = getattr(options["Threads"], "max", None)
        min_thr = getattr(options["Threads"], "min", 1)
        if isinstance(max_thr, int):
            wanted = min(wanted, max_thr)
        if isinstance(min_thr, int):
            wanted = max(wanted, min_thr)
        engine.configure({"Threads": int(wanted)})
    except (AttributeError, TypeError, ValueError):
        _logger.debug("Failed to configure Threads option")
    return wanted


def _configure_hash(
    engine: chess.engine.SimpleEngine,
    options: EngineOptions,
    requested: int | None,
    threads: int,
) -> None:
    """Configure engine hash table size."""
    if "Hash" not in options:
        return
    try:
        target = (
            int(requested) if requested is not None else _auto_hash_mb(threads, options)
        )
        max_hash = getattr(options["Hash"], "max", None)
        min_hash = getattr(options["Hash"], "min", 16)
        if isinstance(max_hash, int):
            target = min(target, max_hash)
        if isinstance(min_hash, int):
            target = max(target, min_hash)
        engine.configure({"Hash": int(target)})
    except (AttributeError, TypeError, ValueError):
        _logger.debug("Failed to configure Hash option")


def _configure_multipv(
    engine: chess.engine.SimpleEngine, options: EngineOptions, requested: int
) -> int:
    """Configure MultiPV and return effective value."""
    effective = max(1, int(requested))
    if "MultiPV" not in options:
        return effective
    try:
        max_mpv = getattr(options["MultiPV"], "max", None)
        if isinstance(max_mpv, int):
            effective = min(effective, max_mpv)
        engine.configure({"MultiPV": int(effective)})
    except (AttributeError, TypeError, ValueError):
        _logger.debug("Failed to configure MultiPV option")
    return effective


def _configure_nnue(engine: chess.engine.SimpleEngine, options: EngineOptions) -> None:
    """Enable NNUE if supported."""
    for nnue_key in ("Use NNUE", "UseNNUE"):
        if nnue_key in options:
            with contextlib.suppress(Exception):
                engine.configure({nnue_key: True})


def _setup_engine(
    args: argparse.Namespace,
) -> tuple[chess.engine.SimpleEngine, int, chess.engine.Limit]:
    """Initialize and configure the chess engine."""
    try:
        engine = chess.engine.SimpleEngine.popen_uci([args.engine])
    except FileNotFoundError:
        _logger.exception("Could not launch engine at: %s", args.engine)
        _logger.exception(
            "Ensure Stockfish is installed and in PATH, or specify with --engine."
        )
        sys.exit(4)

    try:
        options = engine.options  # type: ignore[attr-defined]
    except AttributeError:
        options = {}

    threads = _configure_threads(engine, options, args.threads)
    _configure_hash(engine, options, args.hash_mb, threads)
    effective_mpv = _configure_multipv(engine, options, args.multipv)
    _configure_nnue(engine, options)

    limit: chess.engine.Limit
    if args.depth is not None:
        limit = chess.engine.Limit(depth=args.depth)
    else:
        limit = chess.engine.Limit(time=max(0.05, args.time))

    _log_engine_config(engine, threads, effective_mpv)
    return engine, effective_mpv, limit


def _log_engine_config(
    engine: chess.engine.SimpleEngine, threads: int, multipv: int
) -> None:
    """Log engine configuration summary."""
    try:
        hash_val = engine.options.get("Hash")
        hash_show = int(hash_val.value) if hash_val else None
    except (AttributeError, TypeError, ValueError):
        hash_show = None
    if hash_show is not None:
        _logger.info(
            "Using engine options: Threads=%s, Hash=%s MB, MultiPV=%s",
            threads,
            hash_show,
            multipv,
        )
    else:
        _logger.info("Using engine options: Threads=%s, MultiPV=%s", threads, multipv)


def _get_best_move(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    multipv: int,
) -> chess.Move | None:
    """Get the engine's best move for a position."""
    info_raw = engine.analyse(board, limit=limit, multipv=multipv)
    info = info_raw[0] if isinstance(info_raw, list) else info_raw
    if info is not None and "pv" in info and info["pv"]:
        return info["pv"][0]
    res = engine.play(board, limit)
    return res.move


def _evaluate_position(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    multipv: int,
    *,
    pov_white: bool,
) -> tuple[int | None, int | None]:
    """Evaluate a position and return (cp, mate_in) from POV."""
    info_raw = engine.analyse(board, limit=limit, multipv=multipv)
    info = info_raw[0] if isinstance(info_raw, list) else info_raw
    if info is None or "score" not in info:
        return None, None
    return score_to_cp(info["score"], pov_white=pov_white)


def _classify_mate_move(best_mate: int | None, played_mate: int | None) -> str:
    """Classify a move when mate scores are involved."""
    if best_mate is None or played_mate is None:
        return "Blunder"
    if (best_mate > 0) and (played_mate > 0):
        if abs(played_mate) > abs(best_mate):
            return "Inaccuracy"
        return "Best"
    if (best_mate < 0) and (played_mate < 0):
        if abs(played_mate) < abs(best_mate):
            return "Blunder"
        return "Best" if abs(played_mate) == abs(best_mate) else "Good"
    return "Blunder"


def _analyze_single_move(
    ctx: AnalysisContext, board: chess.Board, move: chess.Move
) -> MoveAnalysis:
    """Analyze a single move and return analysis data."""
    mover_white = board.turn
    san = board.san(move)

    best_move = _get_best_move(ctx.engine, board, ctx.limit, ctx.multipv)
    best_san = board.san(best_move) if best_move is not None else "?"

    board_played = board.copy()
    board_played.push(move)
    played_cp, played_mate = _evaluate_position(
        ctx.engine, board_played, ctx.limit, ctx.multipv, pov_white=mover_white
    )

    if best_move is not None:
        board_best = board.copy()
        board_best.push(best_move)
        best_cp, best_mate = _evaluate_position(
            ctx.engine, board_best, ctx.limit, ctx.multipv, pov_white=mover_white
        )
    else:
        best_cp, best_mate = None, None

    cp_loss: int | None = None
    if best_mate is not None or played_mate is not None:
        classification = _classify_mate_move(best_mate, played_mate)
    elif best_cp is not None and played_cp is not None:
        cp_loss = max(0, best_cp - played_cp)
        classification = classify_cp_loss(cp_loss)
    else:
        classification = "Unknown"

    return MoveAnalysis(
        san=san,
        best_san=best_san,
        played_cp=played_cp,
        played_mate=played_mate,
        best_cp=best_cp,
        best_mate=best_mate,
        cp_loss=cp_loss,
        classification=classification,
    )


def _log_move_analysis(ply: int, result: MoveAnalysis, *, mover_white: bool) -> None:
    """Log a single move's analysis result."""
    side = "W" if mover_white else "B"
    loss_str = str(result.cp_loss) if result.cp_loss is not None else "—"
    _logger.info(
        "%3d  %s   %-8s  %10s  %9s  %5s  %-12s  %s",
        ply,
        side,
        result.san,
        fmt_eval(result.played_cp, result.played_mate),
        fmt_eval(result.best_cp, result.best_mate),
        loss_str,
        result.classification,
        result.best_san,
    )


def _run_analysis(
    game: chess.pgn.Game, ctx: AnalysisContext, *, last_move_only: bool
) -> None:
    """Run the move-by-move analysis."""
    board = game.board()
    _logger.info("Game:")
    white = game.headers.get("White", "White")
    black = game.headers.get("Black", "Black")
    result = game.headers.get("Result", "*")
    _logger.info("  %s vs %s  Result: %s", white, black, result)
    _logger.info("")
    _logger.info(
        "Columns: ply  side  move  played_eval  best_eval  loss  class  best_suggestion"
    )

    if last_move_only:
        _analyze_last_move(game, board, ctx)
    else:
        _analyze_all_moves(game, board, ctx)


def _analyze_last_move(
    node: chess.pgn.Game, board: chess.Board, ctx: AnalysisContext
) -> None:
    """Walk to last move and analyze only that ply."""
    if not node.variations:
        _logger.warning("No moves found in the game.")
        return

    ply = 1
    while node.variations:
        move_node = node.variations[0]
        move = move_node.move

        if not move_node.variations:
            result = _analyze_single_move(ctx, board, move)
            _log_move_analysis(ply, result, mover_white=board.turn)
            break

        board.push(move)
        node = move_node
        ply += 1


def _analyze_all_moves(
    node: chess.pgn.Game, board: chess.Board, ctx: AnalysisContext
) -> None:
    """Analyze all moves in the game."""
    ply = 1
    while node.variations:
        move_node = node.variations[0]
        move = move_node.move
        mover_white = board.turn

        result = _analyze_single_move(ctx, board, move)
        _log_move_analysis(ply, result, mover_white=mover_white)

        node = move_node
        ply += 1
        board.push(move)


def main() -> None:
    """Parse arguments and run chess game analysis."""
    args = _build_argument_parser().parse_args()
    game = _load_game(args.file)
    engine, effective_mpv, limit = _setup_engine(args)
    ctx = AnalysisContext(engine=engine, limit=limit, multipv=effective_mpv)

    try:
        _run_analysis(game, ctx, last_move_only=args.last_move_only)
    finally:
        engine.quit()


if __name__ == "__main__":
    main()

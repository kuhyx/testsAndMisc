#!/usr/bin/env python3
"""Analyze a chess game's moves using a local Stockfish engine and rate each move.

Usage:
    python3 PYTHON/analyze_chess_game.py <path-to-file>
        [--engine stockfish]
        [--time 0.5 | --depth 20]
        [--threads auto|N]
        [--hash-mb auto|MB]
        [--multipv N]
        [--last-move-only]

Notes:
    - Requires python-chess. Install from PYTHON/stockfish_analysis/requirements.txt
    - The input file can be a pure PGN or a log file containing a PGN section.
    - The script tries to locate the PGN by looking for a 'PGN:' marker,
      PGN tags '[...]', or a move list starting with '1.'.
    - Stockfish is CPU-based; it doesn't use GPU VRAM. "Full power" here means
      using many CPU threads and a large transposition table (Hash).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import logging
import multiprocessing
import os
import re
import sys

try:
    import psutil  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency; we fall back if unavailable
    psutil = None  # type: ignore[assignment]

try:
    import chess
    import chess.engine
    import chess.pgn
except Exception:  # pragma: no cover
    logging.exception("Missing dependency. Please install python-chess:")
    logging.exception("  pip install -r PYTHON/stockfish_analysis/requirements.txt")
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
        try:
            return int(psutil.virtual_memory().total // (1024 * 1024))
        except Exception:
            pass
    # Fallback approach for Linux systems using proc meminfo.
    try:
        with open("/proc/meminfo", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= MEMINFO_PARTS_MIN and parts[1].isdigit():
                        # Value is in kB
                        kb = int(parts[1])
                        return kb // 1024
    except Exception:
        pass
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
    except Exception:
        max_allowed = None
    if isinstance(max_allowed, int):
        target = min(target, max_allowed)
    # Some rough scaling: if very many threads, give a bit more (but not huge)
    if threads_wanted >= HIGH_THREAD_COUNT:
        target = min(target + 1024, (total_mb * 3) // 4)
    return max(64, int(target))


def main() -> None:
    """Parse arguments and run chess game analysis."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(
        description="Analyze a chess game's moves with Stockfish and rate each move."
    )
    ap.add_argument("file", help="Path to a PGN file or a log containing a PGN section")
    ap.add_argument(
        "--engine",
        default="stockfish",
        help="Path to stockfish executable (default: stockfish)",
    )
    # Exactly one of time or depth may be provided; default to time
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
    # Performance knobs
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
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        logging.error(f"Input not found: {args.file}")
        sys.exit(1)

    with open(args.file, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    pgn_text = extract_pgn_text(raw)
    if not pgn_text:
        logging.error("Could not locate PGN text in the file.")
        sys.exit(2)

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        logging.error("Failed to parse PGN.")
        sys.exit(3)

    # Prepare engine
    try:
        engine = chess.engine.SimpleEngine.popen_uci([args.engine])
    except FileNotFoundError:
        logging.exception(f"Could not launch engine at: {args.engine}")
        logging.exception(
            "Ensure Stockfish is installed and in PATH, or specify with --engine."
        )
        sys.exit(4)

    # Configure engine performance options if available
    try:
        options = engine.options  # type: ignore[attr-defined]
    except Exception:
        options = {}

    # Threads
    wanted_threads = (
        args.threads if args.threads is not None else (multiprocessing.cpu_count() or 1)
    )
    # Respect engine bounds if present
    if "Threads" in options:
        try:
            max_thr = getattr(options["Threads"], "max", None)
            min_thr = getattr(options["Threads"], "min", 1)
            if isinstance(max_thr, int):
                wanted_threads = min(wanted_threads, max_thr)
            if isinstance(min_thr, int):
                wanted_threads = max(wanted_threads, min_thr)
            engine.configure({"Threads": int(wanted_threads)})
        except Exception:
            pass

    # Configure hash table size in MB.
    if "Hash" in options:
        try:
            if args.hash_mb is not None:
                target_hash = int(args.hash_mb)
            else:
                target_hash = _auto_hash_mb(int(wanted_threads), options)
            # Respect bounds
            max_hash = getattr(options["Hash"], "max", None)
            min_hash = getattr(options["Hash"], "min", 16)
            if isinstance(max_hash, int):
                target_hash = min(target_hash, max_hash)
            if isinstance(min_hash, int):
                target_hash = max(target_hash, min_hash)
            engine.configure({"Hash": int(target_hash)})
        except Exception:
            pass

    # MultiPV
    effective_mpv = max(1, int(args.multipv))
    if "MultiPV" in options:
        try:
            max_mpv = getattr(options["MultiPV"], "max", None)
            if isinstance(max_mpv, int):
                effective_mpv = min(effective_mpv, max_mpv)
            engine.configure({"MultiPV": int(effective_mpv)})
        except Exception:
            pass

    # Enable NNUE if the option exists
    for nnue_key in ("Use NNUE", "UseNNUE"):
        if nnue_key in options:
            with contextlib.suppress(Exception):
                engine.configure({nnue_key: True})

    limit: chess.engine.Limit
    if args.depth is not None:
        limit = chess.engine.Limit(depth=args.depth)
    else:
        limit = chess.engine.Limit(time=max(0.05, args.time))

    board = game.board()
    logging.info("Game:")
    white = game.headers.get("White", "White")
    black = game.headers.get("Black", "Black")
    result = game.headers.get("Result", "*")
    logging.info(f"  {white} vs {black}  Result: {result}")
    logging.info("")
    logging.info(
        "Columns: ply  side  move  played_eval  best_eval  loss  class  best_suggestion"
    )
    # Brief performance summary (best-effort)
    try:
        thr_show = int(wanted_threads)
    except Exception:
        thr_show = 1
    try:
        hash_show = (
            int(engine.options.get("Hash").value)
            if hasattr(engine, "options") and engine.options.get("Hash")
            else None
        )
    except Exception:
        hash_show = None
    if hash_show is not None:
        logging.info(
            f"Using engine options: Threads={thr_show}, "
            f"Hash={hash_show} MB, MultiPV={effective_mpv}"
        )
    else:
        logging.info(
            f"Using engine options: Threads={thr_show}, MultiPV={effective_mpv}"
        )

    ply = 1
    try:
        node = game

        if args.last_move_only:
            # Walk to the last move in the main line and analyze only that ply.
            if not node.variations:
                logging.warning("No moves found in the game.")
            else:
                while node.variations:
                    move_node = node.variations[0]
                    move = move_node.move
                    mover_white = board.turn

                    # If this is the final move in the mainline, analyze it and stop.
                    if not move_node.variations:
                        # Analyse current position to get engine best move suggestion
                        info_root_raw = engine.analyse(
                            board, limit=limit, multipv=effective_mpv
                        )
                        info_root = (
                            info_root_raw[0]
                            if isinstance(info_root_raw, list)
                            else info_root_raw
                        )
                        best_move = None
                        if (
                            info_root is not None
                            and "pv" in info_root
                            and info_root["pv"]
                        ):
                            best_move = info_root["pv"][0]
                        if best_move is None:
                            res = engine.play(board, limit)
                            best_move = res.move

                        san = board.san(move)

                        # Evaluate played move
                        board_played = board.copy()
                        board_played.push(move)
                        info_played_raw = engine.analyse(
                            board_played, limit=limit, multipv=effective_mpv
                        )
                        info_played = (
                            info_played_raw[0]
                            if isinstance(info_played_raw, list)
                            else info_played_raw
                        )
                        if info_played is None or "score" not in info_played:
                            played_cp, played_mate = None, None
                        else:
                            played_cp, played_mate = score_to_cp(
                                info_played["score"], pov_white=mover_white
                            )

                        # Evaluate best move position (for mover POV)
                        best_san = (
                            board.san(best_move) if best_move is not None else "?"
                        )
                        if best_move is not None:
                            board_best = board.copy()
                            board_best.push(best_move)
                            info_best_raw = engine.analyse(
                                board_best, limit=limit, multipv=effective_mpv
                            )
                            info_best = (
                                info_best_raw[0]
                                if isinstance(info_best_raw, list)
                                else info_best_raw
                            )
                            if info_best is None or "score" not in info_best:
                                best_cp, best_mate = None, None
                            else:
                                best_cp, best_mate = score_to_cp(
                                    info_best["score"], pov_white=mover_white
                                )
                        else:
                            best_cp, best_mate = None, None

                        # Compute loss/classification
                        cp_loss: int | None = None
                        classification = "Unknown"
                        if best_mate is not None or played_mate is not None:
                            if best_mate is not None and played_mate is not None:
                                if (best_mate > 0) and (played_mate > 0):
                                    if abs(played_mate) == abs(best_mate):
                                        classification = "Best"
                                    elif abs(played_mate) > abs(best_mate):
                                        classification = "Inaccuracy"
                                    else:
                                        classification = "Best"
                                elif (best_mate < 0) and (played_mate < 0):
                                    if abs(played_mate) == abs(best_mate):
                                        classification = "Best"
                                    elif abs(played_mate) < abs(best_mate):
                                        classification = "Blunder"
                                    else:
                                        classification = "Good"
                                else:
                                    classification = "Blunder"
                            else:
                                classification = "Blunder"
                        elif best_cp is not None and played_cp is not None:
                            cp_loss = max(0, best_cp - played_cp)
                            classification = classify_cp_loss(cp_loss)

                        side = "W" if mover_white else "B"
                        logging.info(
                            f"{ply:>3}  {side}   {san:<8}  "
                            f"{fmt_eval(played_cp, played_mate):>10}  "
                            f"{fmt_eval(best_cp, best_mate):>9}  "
                            f"{(str(cp_loss) if cp_loss is not None else '—'):>5}  "
                            f"{classification:<12}  {best_san}"
                        )
                        break

                    # Advance to keep searching for the last move
                    board.push(move)
                    node = move_node
                    ply += 1
        else:
            # Default behavior: analyze all moves
            while node.variations:
                move_node = node.variations[0]
                move = move_node.move
                mover_white = board.turn

                # Analyse position to get engine best move suggestion
                info_root_raw = engine.analyse(
                    board, limit=limit, multipv=effective_mpv
                )
                info_root = (
                    info_root_raw[0]
                    if isinstance(info_root_raw, list)
                    else info_root_raw
                )
                best_move = None
                if info_root is not None and "pv" in info_root and info_root["pv"]:
                    best_move = info_root["pv"][0]
                # Fallback to engine.play if PV missing
                if best_move is None:
                    res = engine.play(board, limit)
                    best_move = res.move

                # Evaluate played move position (for mover POV) using a temp board
                san = board.san(move)
                board_played = board.copy()
                board_played.push(move)
                info_played_raw = engine.analyse(
                    board_played, limit=limit, multipv=effective_mpv
                )
                info_played = (
                    info_played_raw[0]
                    if isinstance(info_played_raw, list)
                    else info_played_raw
                )
                if info_played is None or "score" not in info_played:
                    played_cp, played_mate = None, None
                else:
                    played_cp, played_mate = score_to_cp(
                        info_played["score"], pov_white=mover_white
                    )

                # Evaluate best move position (for mover POV)
                best_san = board.san(best_move) if best_move is not None else "?"
                if best_move is not None:
                    board_best = board.copy()
                    board_best.push(best_move)
                    info_best_raw = engine.analyse(
                        board_best, limit=limit, multipv=effective_mpv
                    )
                    info_best = (
                        info_best_raw[0]
                        if isinstance(info_best_raw, list)
                        else info_best_raw
                    )
                    if info_best is None or "score" not in info_best:
                        best_cp, best_mate = None, None
                    else:
                        best_cp, best_mate = score_to_cp(
                            info_best["score"], pov_white=mover_white
                        )
                else:
                    best_cp, best_mate = None, None

                # Compute centipawn loss bands
                cp_loss: int | None = None
                classification = "Unknown"
                # Handle mate cases first
                if best_mate is not None or played_mate is not None:
                    if best_mate is not None and played_mate is not None:
                        # Same sign -> compare speed
                        if (best_mate > 0) and (played_mate > 0):
                            # Keeping a mate: equal speed Best;
                            # slower -> Inaccuracy; faster -> Best
                            if abs(played_mate) == abs(best_mate):
                                classification = "Best"
                            elif abs(played_mate) > abs(best_mate):
                                classification = "Inaccuracy"
                            else:
                                classification = "Best"
                        elif (best_mate < 0) and (played_mate < 0):
                            # Defending: equal delay Best;
                            # sooner mate -> Blunder;
                            # if played delays more -> Good
                            if abs(played_mate) == abs(best_mate):
                                classification = "Best"
                            elif abs(played_mate) < abs(best_mate):
                                classification = "Blunder"
                            else:
                                classification = "Good"
                        else:
                            # Sign flip across who mates -> Blunder
                            classification = "Blunder"
                    else:
                        # Losing a forced mate or missing one
                        classification = "Blunder"
                elif best_cp is not None and played_cp is not None:
                    cp_loss = max(0, best_cp - played_cp)
                    classification = classify_cp_loss(cp_loss)

                side = "W" if mover_white else "B"
                logging.info(
                    f"{ply:>3}  {side}   {san:<8}  "
                    f"{fmt_eval(played_cp, played_mate):>10}  "
                    f"{fmt_eval(best_cp, best_mate):>9}  "
                    f"{(str(cp_loss) if cp_loss is not None else '—'):>5}  "
                    f"{classification:<12}  {best_san}"
                )

                node = move_node
                ply += 1
                # Advance the live board for the next ply
                board.push(move)
    finally:
        engine.quit()


if __name__ == "__main__":
    main()

# Chess move analysis with Stockfish

This utility parses a PGN (or a log that contains a PGN section) and evaluates each move with a local Stockfish engine, printing a per-move quality rating.

## Install

Install python dependencies:

```
pip install -r PYTHON/stockfish_analysis/requirements.txt
```

Ensure Stockfish is installed and available in your PATH (or provide the path via `--engine`). On Linux, you can typically install with your package manager or download a binary.

## Run

From the repo root:

```
python3 PYTHON/analyze_chess_game.py lichess_bot_game_8GSdY3Ci.log
```

Options:

- `--engine /path/to/stockfish` to specify a custom engine path
- `--time 0.2` seconds per evaluation (default)
- `--depth 12` fixed depth instead of time

The script prints a table with, for each ply:

- side to move, SAN move, eval before/after from mover's POV, delta, classification, and Stockfish best move suggestion.

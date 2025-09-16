# Opening Learner (C + SDL2)

- Click a piece, then click a destination to move.
- Thick board outline, board uses non-pure colors.
- Uses local Stockfish or asmfish via UCI.
- Logs mistakes to `mistakes.txt` and lets you revisit them with the `m` key.

Build and check:

```sh
./check_build.sh
```

Run:

```sh
./opening_learner
```

Tips:
- ESC clears selection.
- Press `m` to cycle to a stored mistake position and practice the best move there.
- If you play Black, the board flips so Black is at the bottom.

Notes:
- Rendering avoids TTF dependency; pieces are clear, high-contrast geometric glyphs.

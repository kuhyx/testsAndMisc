## Sliding-Square Puzzle Solver

Parses a screenshot of a sliding-square puzzle and solves it via BFS.

### Setup

```bash
cd puzzle_solver
python -m venv .venv && source .venv/bin/activate
pip install opencv-python-headless numpy
```

### Usage

```bash
# From workspace root, with venv active:

# Step 1 – Parse screenshot to editable JSON
python -m puzzle_solver parse screenshot.png -o puzzle.json

# Step 2 – Review & fix any "unknown" squares in puzzle.json
#   (set "type" to: normal / portal / teleporter / key / lock)

# Step 3 – Solve
python -m puzzle_solver solve puzzle.json

# One-shot (no manual review)
python -m puzzle_solver run screenshot.png

# Debug overlay (visualise detected squares on image)
python -m puzzle_solver debug screenshot.png -o debug.png
```

### Game mechanics

| Square              | JSON type    | Description                                       |
| ------------------- | ------------ | ------------------------------------------------- |
| Empty outline       | `normal`     | Regular landing square                            |
| Solid fill          | `player`     | Starting position                                 |
| Ring inside         | `goal`       | Target destination                                |
| Inner square offset | `portal`     | Pass through from the side marked by `"side"`     |
| Antenna line(s)     | `teleporter` | Warp to paired teleporter (`"group"` id)          |
| Key symbol          | `key`        | Removes matching lock (`"lock_id"`)               |
| Lock symbol         | `lock`       | Solid until matching key collected, then vanishes |

### Movement

You slide in a cardinal direction (up/down/left/right) until you hit
another square. If you slide off the grid without hitting anything, you
die.

### Algorithm

BFS over state = `(position, set_of_active_locks)`. Explores all
reachable states and returns the shortest move sequence to the goal.

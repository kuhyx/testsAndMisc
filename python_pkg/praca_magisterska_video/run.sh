#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"
[[ ! -d "$VENV" ]] && python3 -m venv "$VENV"
"$VENV/bin/pip" show moviepy &>/dev/null || "$VENV/bin/pip" install moviepy numpy -q
export PYTHONUNBUFFERED=1
# Run all visualizations
echo "==> Rendering visualize_q02 (Dijkstra/Bellman-Ford/A*)"
"$VENV/bin/python" "$SCRIPT_DIR/visualize_q02.py" "$@"
echo "==> Rendering visualize_q23"
"$VENV/bin/python" "$SCRIPT_DIR/visualize_q23.py" "$@"
echo "==> Rendering visualize_q24"
"$VENV/bin/python" "$SCRIPT_DIR/visualize_q24.py" "$@"
echo "Done."

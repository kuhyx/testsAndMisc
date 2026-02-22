#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"
[[ ! -d "$VENV" ]] && python3 -m venv "$VENV"
"$VENV/bin/pip" show opencv-python &>/dev/null || "$VENV/bin/pip" install opencv-python -q
# Usage: ./run.sh <images_dir>
"$VENV/bin/python" "$SCRIPT_DIR/tag_divider.py" "$@"

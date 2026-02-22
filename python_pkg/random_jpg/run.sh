#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"
[[ ! -d "$VENV" ]] && python3 -m venv "$VENV"
"$VENV/bin/pip" show pillow &>/dev/null || "$VENV/bin/pip" install pillow -q
"$VENV/bin/python" "$SCRIPT_DIR/generate_jpeg.py" "$@"

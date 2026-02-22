#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"
[[ ! -d "$VENV" ]] && python3 -m venv "$VENV"
"$VENV/bin/pip" show torch &>/dev/null || "$VENV/bin/pip" install torch transformers numpy scipy bark -q
echo "Loading models (this may take a minute on first run)..."
export PYTHONUNBUFFERED=1
"$VENV/bin/python" "$SCRIPT_DIR/music_generator.py" "$@"

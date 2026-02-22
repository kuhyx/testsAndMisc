#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Usage: ./run.sh <text_file> [options]
"$SCRIPT_DIR/../../.venv/bin/python" "$SCRIPT_DIR/vocabulary_curve.py" "$@"

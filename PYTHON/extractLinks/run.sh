#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run the extractor. Usage:
#   ./run.sh path/to/input.html [output.txt]

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <input.html> [output.txt]" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/main.py" "$@"

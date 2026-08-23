#!/usr/bin/env bash
# Backwards compatibility wrapper; prefer using detect_gpu.sh directly.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./detect_gpu.sh disable=SC1091
. "$SCRIPT_DIR/detect_gpu.sh"

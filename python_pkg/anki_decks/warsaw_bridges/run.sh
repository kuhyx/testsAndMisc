#!/bin/bash
# Script to generate Warsaw Bridges Anki deck

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PREVIEW_DIR="$SCRIPT_DIR/preview_images"

echo "=== Warsaw Bridges Anki Generator ==="
echo

if [ ! -d "$VENV_DIR" ]; then
	echo "Creating virtual environment..."
	python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip show genanki &>/dev/null || pip install --quiet matplotlib genanki geopandas requests shapely

cd "$SCRIPT_DIR"

# Create preview images directory
mkdir -p "$PREVIEW_DIR"

python -m warsaw_bridges_anki --output warsaw_bridges.apkg --preview "$PREVIEW_DIR" --preview-count 5

echo
echo "Done! The Anki deck is at: $SCRIPT_DIR/warsaw_bridges.apkg"
echo "Preview images are in: $PREVIEW_DIR"

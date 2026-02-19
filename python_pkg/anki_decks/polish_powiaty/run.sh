#!/bin/bash
# Script to generate Polish Powiaty Anki deck

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PREVIEW_DIR="$SCRIPT_DIR/preview_images"

echo "=== Polish Powiaty Anki Generator ==="
echo

if [ ! -d "$VENV_DIR" ]; then
	echo "Creating virtual environment..."
	python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet matplotlib genanki geopandas

cd "$SCRIPT_DIR"

# Create preview images directory
mkdir -p "$PREVIEW_DIR"

python -m polish_powiaty_anki --output polish_powiaty.apkg --preview "$PREVIEW_DIR" --preview-count 5

echo
echo "Done! The Anki deck is at: $SCRIPT_DIR/polish_powiaty.apkg"
echo "Preview images are in: $PREVIEW_DIR"

#!/bin/bash
# Script to generate Warsaw Landmarks Anki deck

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PREVIEW_DIR="$SCRIPT_DIR/preview_images"

echo "=== Warsaw Landmarks Anki Generator ==="
echo

if [ ! -d "$VENV_DIR" ]; then
	echo "Creating virtual environment..."
	python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet matplotlib genanki geopandas requests shapely

cd "$SCRIPT_DIR"

# Create preview images directory
mkdir -p "$PREVIEW_DIR"

python -m warsaw_landmarks_anki --output warsaw_landmarks.apkg --preview "$PREVIEW_DIR" --preview-count 5

echo
echo "Done! The Anki deck is at: $SCRIPT_DIR/warsaw_landmarks.apkg"
echo "Preview images are in: $PREVIEW_DIR"

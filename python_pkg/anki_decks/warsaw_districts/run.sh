#!/bin/bash
# Script to set up environment, install dependencies, and generate Warsaw Districts Anki deck

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PREVIEW_DIR="$SCRIPT_DIR/preview_images"

echo "=== Warsaw Districts Anki Generator ==="
echo

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet matplotlib genanki geopandas

# Export preview images
echo
echo "Exporting preview images to $PREVIEW_DIR..."
mkdir -p "$PREVIEW_DIR"
cd "$SCRIPT_DIR"
python -c "
from warsaw_districts_anki import WARSAW_DISTRICTS, generate_district_image_bytes
from pathlib import Path

preview_dir = Path('$PREVIEW_DIR')
for district in WARSAW_DISTRICTS:
    filename = district.replace(' ', '_').replace('-', '_') + '.png'
    filepath = preview_dir / filename
    filepath.write_bytes(generate_district_image_bytes(district))
    print(f'  Exported: {filename}')
"

echo
echo "Preview images exported! Check: $PREVIEW_DIR"

# Generate Anki deck
echo
echo "Generating Anki flashcards..."
python -m warsaw_districts_anki --output warsaw_districts.apkg

echo
echo "Done!"
echo "  - Preview images: $PREVIEW_DIR"
echo "  - Anki deck: $SCRIPT_DIR/warsaw_districts.apkg"

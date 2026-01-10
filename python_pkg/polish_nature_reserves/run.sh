#!/bin/bash
# Run the Polish nature reserves Anki generator

cd "$(dirname "$0")" || exit

# Default runs all reserves - use --limit for testing
python polish_nature_reserves_anki.py --preview preview_images --preview-count 5 "$@"

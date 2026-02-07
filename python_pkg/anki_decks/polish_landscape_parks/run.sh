#!/bin/bash
# Run the Polish landscape parks Anki generator

cd "$(dirname "$0")" || exit

python polish_landscape_parks_anki.py --preview preview_images --preview-count 5 "$@"

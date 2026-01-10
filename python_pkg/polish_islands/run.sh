#!/bin/bash
# Run the Polish islands Anki generator

cd "$(dirname "$0")" || exit

python polish_islands_anki.py --preview preview_images --preview-count 5 "$@"

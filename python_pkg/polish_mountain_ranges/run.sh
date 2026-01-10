#!/bin/bash
# Run the Polish mountain ranges Anki generator

cd "$(dirname "$0")" || exit

python polish_mountain_ranges_anki.py --preview preview_images --preview-count 5 "$@"

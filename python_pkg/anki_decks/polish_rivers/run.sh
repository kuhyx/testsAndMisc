#!/bin/bash
# Run the Polish rivers Anki generator

cd "$(dirname "$0")" || exit

python polish_rivers_anki.py --preview preview_images --preview-count 5 "$@"

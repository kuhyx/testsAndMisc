#!/bin/bash
# Run the Polish UNESCO sites Anki generator

cd "$(dirname "$0")" || exit

python polish_unesco_sites_anki.py --preview preview_images --preview-count 5 "$@"

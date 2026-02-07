#!/bin/bash
# Run the Polish forests Anki generator

cd "$(dirname "$0")" || exit

python polish_forests_anki.py --preview preview_images --preview-count 5 "$@"

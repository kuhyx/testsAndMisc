#!/bin/bash
# Run the Polish lakes Anki generator

cd "$(dirname "$0")" || exit

python polish_lakes_anki.py --preview preview_images --preview-count 5 "$@"

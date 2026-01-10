#!/bin/bash
# Run the Polish national parks Anki generator

cd "$(dirname "$0")" || exit

python polish_national_parks_anki.py --preview preview_images --preview-count 5 "$@"

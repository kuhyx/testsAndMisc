#!/bin/bash
# Run the Polish mountain peaks Anki generator

cd "$(dirname "$0")" || exit

python polish_mountain_peaks_anki.py --preview preview_images --preview-count 5 "$@"

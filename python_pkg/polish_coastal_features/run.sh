#!/bin/bash
# Run the Polish coastal features Anki generator

cd "$(dirname "$0")" || exit

python polish_coastal_features_anki.py --preview preview_images --preview-count 5 "$@"

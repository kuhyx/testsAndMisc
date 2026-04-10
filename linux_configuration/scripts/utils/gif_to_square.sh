#!/usr/bin/env bash
# Pad a GIF to a square with transparent background, centered.
# Useful for making Slack emojis from rectangular GIFs.
# Usage: gif_to_square.sh <input.gif> [output.gif] [background]

set -euo pipefail

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Default background color (transparent)
DEFAULT_BG="none"

# Function to display usage
usage() {
  cat << EOF
Usage: $0 <input.gif> [output.gif] [background]

Arguments:
    input.gif       Path to the input GIF file (required)
    output.gif      Path to the output GIF file (default: <input>_square.gif)
    background      Background color for padding (default: ${DEFAULT_BG})
                    Use "none" for transparent, or any color name/hex

Examples:
    $0 emoji.gif
    $0 emoji.gif square_emoji.gif
    $0 emoji.gif square_emoji.gif white
    $0 emoji.gif square_emoji.gif "#FF0000"

Note: Requires ImageMagick (magick or convert command)
      Slack emoji max size: 128x128 pixels, 256KB
EOF
  exit 1
}

# Install ImageMagick if missing
if ! command -v magick &> /dev/null && ! command -v convert &> /dev/null; then
  echo "ImageMagick not found. Installing..."
  if command -v pacman &> /dev/null; then
    sudo pacman -S --noconfirm imagemagick
  elif command -v apt-get &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y imagemagick
  else
    echo "Error: Could not detect package manager. Install ImageMagick manually."
    exit 1
  fi
fi

require_imagemagick || exit 1

# Set up identify command (IM7: magick identify, IM6: identify)
if [[ ${MAGICK_CMD} == "magick" ]]; then
  IDENTIFY_CMD="magick identify"
else
  IDENTIFY_CMD="identify"
fi

# Parse arguments
if [[ $# -lt 1 ]]; then
  echo "Error: Missing required argument <input.gif>"
  usage
fi

INPUT_GIF="$1"
OUTPUT_GIF="${2:-}"
BACKGROUND="${3:-${DEFAULT_BG}}"  # Reserved for future padding mode
export BACKGROUND

# Validate input file exists
if [[ ! -f ${INPUT_GIF} ]]; then
  echo "Error: Input file '${INPUT_GIF}' does not exist."
  exit 1
fi

# Validate it's a GIF
MIME_TYPE=$(file --mime-type -b "${INPUT_GIF}")
if [[ ${MIME_TYPE} != "image/gif" ]]; then
  echo "Error: '${INPUT_GIF}' is not a GIF file (detected: ${MIME_TYPE})"
  exit 1
fi

# Generate output filename if not provided
if [[ -z ${OUTPUT_GIF} ]]; then
  OUTPUT_GIF=$(generate_output_filename "${INPUT_GIF}" "_square")
fi

# Get dimensions of the first frame
DIMENSIONS=$(${IDENTIFY_CMD} -format "%wx%h" "${INPUT_GIF}[0]")
WIDTH="${DIMENSIONS%x*}"
HEIGHT="${DIMENSIONS#*x}"

echo "Input: ${INPUT_GIF}"
echo "Dimensions: ${WIDTH}x${HEIGHT}"

if [[ ${WIDTH} -eq ${HEIGHT} ]]; then
  echo "Image is already square. Copying to output."
  cp "${INPUT_GIF}" "${OUTPUT_GIF}"
else
  # Stretch to square using the larger dimension
  if [[ ${WIDTH} -gt ${HEIGHT} ]]; then
    SIDE=${WIDTH}
  else
    SIDE=${HEIGHT}
  fi

  echo "Stretching to ${SIDE}x${SIDE}..."

  "${MAGICK_CMD}" "${INPUT_GIF}" \
    -coalesce \
    -resize "${SIDE}x${SIDE}!" \
    -layers Optimize \
    "${OUTPUT_GIF}"
fi

if [[ -f ${OUTPUT_GIF} ]]; then
  OUT_DIMENSIONS=$(${IDENTIFY_CMD} -format "%wx%h" "${OUTPUT_GIF}[0]")
  INPUT_SIZE=$(du -h "${INPUT_GIF}" | cut -f1)
  OUTPUT_SIZE=$(du -h "${OUTPUT_GIF}" | cut -f1)

  echo "✓ Successfully created square GIF"
  echo "Output: ${OUTPUT_GIF} (${OUT_DIMENSIONS})"
  echo "Input size:  ${INPUT_SIZE}"
  echo "Output size: ${OUTPUT_SIZE}"

  # Auto-shrink if over Slack's 128KB emoji limit (target 124KB for safety margin)
  MAX_BYTES=126976
  OUTPUT_BYTES=$(stat -c%s "${OUTPUT_GIF}" 2>/dev/null || stat -f%z "${OUTPUT_GIF}" 2>/dev/null)
  if [[ ${OUTPUT_BYTES} -gt ${MAX_BYTES} ]]; then
    echo ""
    echo "Output is over 128KB (${OUTPUT_BYTES} bytes). Auto-shrinking for Slack..."
    CURRENT_SIDE=$(${IDENTIFY_CMD} -format "%w" "${OUTPUT_GIF}[0]")
    while [[ ${OUTPUT_BYTES} -gt ${MAX_BYTES} && ${CURRENT_SIDE} -gt 16 ]]; do
      # Reduce by ~25% each iteration
      CURRENT_SIDE=$(( CURRENT_SIDE * 75 / 100 ))
      echo "  Trying ${CURRENT_SIDE}x${CURRENT_SIDE}..."
      "${MAGICK_CMD}" "${OUTPUT_GIF}" \
        -coalesce \
        -resize "${CURRENT_SIDE}x${CURRENT_SIDE}!" \
        -layers Optimize \
        "${OUTPUT_GIF}"
      OUTPUT_BYTES=$(stat -c%s "${OUTPUT_GIF}" 2>/dev/null || stat -f%z "${OUTPUT_GIF}" 2>/dev/null)
    done
    OUTPUT_SIZE=$(du -h "${OUTPUT_GIF}" | cut -f1)
    echo "✓ Shrunk to ${CURRENT_SIDE}x${CURRENT_SIDE} (${OUTPUT_SIZE}, ${OUTPUT_BYTES} bytes)"
  fi
else
  echo "✗ Error: Failed to create output file"
  exit 1
fi

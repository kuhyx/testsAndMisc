#!/usr/bin/env bash
# Convert a text file to image(s) with specified resolution
# Default resolution: 320x240
# Automatically splits text into multiple images if it doesn't fit
# Usage: txt_to_image.sh <input_text_file> [resolution] [output_prefix]

set -euo pipefail

# Default resolution
DEFAULT_RESOLUTION="320x240"

# Function to display usage
usage() {
  cat << EOF
Usage: $0 <input_text_file> [resolution] [output_prefix]

Arguments:
    input_text_file Path to the input text file (required)
    resolution      Target resolution in WIDTHxHEIGHT format (default: ${DEFAULT_RESOLUTION})
    output_prefix   Prefix for output image files (default: <input_filename>)

Examples:
    $0 notes.txt
    $0 notes.txt 640x480
    $0 notes.txt 320x240 output

Note: Requires ImageMagick (magick or convert command)
EOF
  exit 1
}

# Check if ImageMagick is installed and determine which command to use
if command -v magick &> /dev/null; then
  MAGICK_CMD="magick"
elif command -v convert &> /dev/null; then
  MAGICK_CMD="convert"
else
  echo "Error: ImageMagick is not installed."
  echo "Install it with:"
  echo "  Arch Linux: sudo pacman -S imagemagick"
  echo "  Ubuntu/Debian: sudo apt install imagemagick"
  exit 1
fi

# Parse arguments
if [[ $# -lt 1 ]]; then
  echo "Error: Missing required argument <input_text_file>"
  usage
fi

INPUT_FILE="$1"
RESOLUTION="${2:-${DEFAULT_RESOLUTION}}"
OUTPUT_PREFIX="${3:-}"

# Validate input file exists
if [[ ! -f ${INPUT_FILE} ]]; then
  echo "Error: Input file '${INPUT_FILE}' does not exist."
  exit 1
fi

# Validate resolution format (WIDTHxHEIGHT)
if [[ ! ${RESOLUTION} =~ ^[0-9]+x[0-9]+$ ]]; then
  echo "Error: Invalid resolution format '${RESOLUTION}'"
  echo "Expected format: WIDTHxHEIGHT (e.g., 320x240, 1920x1080)"
  exit 1
fi

# Extract width and height
WIDTH=$(echo "${RESOLUTION}" | cut -d'x' -f1)
HEIGHT=$(echo "${RESOLUTION}" | cut -d'x' -f2)

# Calculate font size based on resolution
FONT_SIZE=$((WIDTH / 30))
if [[ ${FONT_SIZE} -lt 8 ]]; then
  FONT_SIZE=8
fi

# Generate output prefix if not provided
if [[ -z ${OUTPUT_PREFIX} ]]; then
  BASENAME=$(basename "${INPUT_FILE}")
  FILENAME="${BASENAME%.*}"
  DIRNAME=$(dirname "${INPUT_FILE}")
  OUTPUT_PREFIX="${DIRNAME}/${FILENAME}"
fi

# Calculate lines per image based on resolution and font size
# Rough estimate: height / (font_size * 1.5) for line spacing
LINES_PER_IMAGE=$((HEIGHT / (FONT_SIZE * 3 / 2)))
if [[ ${LINES_PER_IMAGE} -lt 5 ]]; then
  LINES_PER_IMAGE=5
fi

echo "Converting text file to image(s)..."
echo "Resolution: ${RESOLUTION}"
echo "Font size: ${FONT_SIZE}"
echo "Estimated lines per image: ${LINES_PER_IMAGE}"

# Read the file and count total lines
mapfile -t LINES < "${INPUT_FILE}"
TOTAL_LINES=${#LINES[@]}

echo "Total lines in file: ${TOTAL_LINES}"

# Calculate number of images needed
NUM_IMAGES=$(((TOTAL_LINES + LINES_PER_IMAGE - 1) / LINES_PER_IMAGE))

echo "Creating ${NUM_IMAGES} image(s)..."

# Create temporary directory for chunks
TEMP_DIR=$(mktemp -d)
trap 'rm -rf ${TEMP_DIR}' EXIT

# Split text into chunks and create images
IMAGE_COUNT=0
for ((i = 0; i < TOTAL_LINES; i += LINES_PER_IMAGE)); do
  IMAGE_COUNT=$((IMAGE_COUNT + 1))

  # Calculate end line for this chunk
  END_LINE=$((i + LINES_PER_IMAGE))
  if [[ ${END_LINE} -gt ${TOTAL_LINES} ]]; then
    END_LINE=${TOTAL_LINES}
  fi

  # Create chunk file
  CHUNK_FILE="${TEMP_DIR}/chunk_${IMAGE_COUNT}.txt"
  for ((j = i; j < END_LINE; j++)); do
    echo "${LINES[$j]}" >> "${CHUNK_FILE}"
  done

  # Determine output filename
  if [[ ${NUM_IMAGES} -eq 1 ]]; then
    OUTPUT_FILE="${OUTPUT_PREFIX}.png"
  else
    OUTPUT_FILE="${OUTPUT_PREFIX}_$(printf "%03d" ${IMAGE_COUNT}).png"
  fi

  echo "  Creating image ${IMAGE_COUNT}/${NUM_IMAGES}: ${OUTPUT_FILE}"

  # Create image from text
  # Using label: instead of caption: for better control
  if ${MAGICK_CMD} -size "${WIDTH}x${HEIGHT}" \
    -background white \
    -fill black \
    -font "DejaVu-Sans-Mono" \
    -pointsize "${FONT_SIZE}" \
    -gravity northwest \
    label:@"${CHUNK_FILE}" \
    -extent "${WIDTH}x${HEIGHT}" \
    "${OUTPUT_FILE}"; then
    OUTPUT_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    echo "    ✓ Created: ${OUTPUT_FILE} (${OUTPUT_SIZE})"
  else
    echo "    ✗ Failed to create: ${OUTPUT_FILE}"
    exit 1
  fi
done

echo ""
echo "✓ Successfully created ${IMAGE_COUNT} image(s)"
echo "Output files:"
if [[ ${NUM_IMAGES} -eq 1 ]]; then
  echo "  ${OUTPUT_PREFIX}.png"
else
  echo "  ${OUTPUT_PREFIX}_001.png to ${OUTPUT_PREFIX}_$(printf "%03d" ${IMAGE_COUNT}).png"
fi

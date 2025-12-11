#!/usr/bin/env bash
# Convert an image to a specified resolution
# Default resolution: 320x240
# Usage: image_to_resolution.sh <input_image> [resolution] [output_image]

set -euo pipefail

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Default resolution
DEFAULT_RESOLUTION="320x240"

# Function to display usage
usage() {
	cat <<EOF
Usage: $0 <input_image> [resolution] [output_image]

Arguments:
    input_image     Path to the input image file (required)
    resolution      Target resolution in WIDTHxHEIGHT format (default: ${DEFAULT_RESOLUTION})
    output_image    Path to the output image file (default: <input>_<resolution>.<ext>)

Examples:
    $0 photo.jpg
    $0 photo.jpg 640x480
    $0 photo.jpg 1920x1080 output.jpg
    $0 image.png 320x240 resized.png

Note: Requires ImageMagick (convert command)
EOF
	exit 1
}

# Check if ImageMagick is installed
require_imagemagick "convert" || exit 1

# Parse arguments
if [[ $# -lt 1 ]]; then
	echo "Error: Missing required argument <input_image>"
	usage
fi

INPUT_IMAGE="$1"
RESOLUTION="${2:-${DEFAULT_RESOLUTION}}"
OUTPUT_IMAGE="${3:-}"

# Validate input image exists
if [[ ! -f ${INPUT_IMAGE} ]]; then
	echo "Error: Input image '${INPUT_IMAGE}' does not exist."
	exit 1
fi

# Validate resolution format (WIDTHxHEIGHT)
if ! validate_resolution "$RESOLUTION"; then
	echo "Error: Invalid resolution format '${RESOLUTION}'"
	echo "Expected format: WIDTHxHEIGHT (e.g., 320x240, 1920x1080)"
	exit 1
fi

# Generate output filename if not provided
if [[ -z ${OUTPUT_IMAGE} ]]; then
	OUTPUT_IMAGE=$(generate_output_filename "${INPUT_IMAGE}" "_${RESOLUTION}")
fi

# Perform the conversion
echo "Converting '${INPUT_IMAGE}' to ${RESOLUTION}..."
echo "Output will be saved to: ${OUTPUT_IMAGE}"

if convert "${INPUT_IMAGE}" -resize "${RESOLUTION}!" "${OUTPUT_IMAGE}"; then
	echo "✓ Successfully converted image to ${RESOLUTION}"
	echo "Output: ${OUTPUT_IMAGE}"

	# Show file sizes
	INPUT_SIZE=$(du -h "${INPUT_IMAGE}" | cut -f1)
	OUTPUT_SIZE=$(du -h "${OUTPUT_IMAGE}" | cut -f1)
	echo "Input size:  ${INPUT_SIZE}"
	echo "Output size: ${OUTPUT_SIZE}"
else
	echo "✗ Error: Conversion failed"
	exit 1
fi

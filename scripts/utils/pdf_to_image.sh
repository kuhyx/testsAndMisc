#!/usr/bin/env bash

set -euo pipefail

# pdf_to_png.sh (magick-only backend, behaves like pdf_to_image)
#
# Convert one or more PDF files to image files using ImageMagick v7 `magick`.
# Default output format is jpg, but can be changed with -f.

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

OUTPUT_DIR=""
OUTPUT_FORMAT="jpg"
PDF_FILES=()

usage() {
	cat <<EOF
Usage:
  $(basename "$0") [OPTIONS] PDF_FILE [PDF_FILE...]

Convert one or more PDF files to images using ImageMagick 'magick'.

Options:
  -o DIR     Output directory (default: current directory)
  -f FORMAT  Output image format (default: jpg)
  -h         Show this help

Examples:
  $(basename "$0") file.pdf
  $(basename "$0") -f png file1.pdf file2.pdf
  $(basename "$0") -o out -f webp file.pdf
EOF
}

ensure_magick() {
	require_imagemagick "magick" || exit 1
}

parse_args() {
	local opt
	OUTPUT_DIR=""
	OUTPUT_FORMAT="jpg"
	PDF_FILES=()

	while getopts ":o:f:h" opt; do
		case "$opt" in
		o)
			OUTPUT_DIR="$OPTARG"
			;;
		f)
			OUTPUT_FORMAT="$OPTARG"
			;;
		h)
			usage
			exit 0
			;;
		*)
			usage
			exit 1
			;;
		esac
	done

	shift $((OPTIND - 1))

	if [[ $# -lt 1 ]]; then
		echo "Error: at least one PDF file must be specified." >&2
		usage
		exit 1
	fi

	PDF_FILES=("$@")

	if [[ -z ${OUTPUT_DIR:-} ]]; then
		OUTPUT_DIR="${PWD}"
	fi

	if [[ ! -d $OUTPUT_DIR ]]; then
		mkdir -p "$OUTPUT_DIR"
	fi
}

convert_pdf() {
	local pdf_file="$1"
	local base name out_pattern

	name="$(basename "$pdf_file")"
	base="${name%.*}"
	out_pattern="${OUTPUT_DIR%/}/${base}_page-"

	log "Converting '$pdf_file' to $OUTPUT_FORMAT using magick -> ${out_pattern}*.${OUTPUT_FORMAT}"
	magick -density 300 "$pdf_file" -quality 90 "${out_pattern}%d.${OUTPUT_FORMAT}"
}

main() {
	ensure_magick
	parse_args "$@"

	local pdf
	for pdf in "${PDF_FILES[@]}"; do
		if [[ ! -f $pdf ]]; then
			echo "Warning: '$pdf' is not a regular file, skipping." >&2
			continue
		fi

		convert_pdf "$pdf"
	done

	log "Done converting PDFs to ${OUTPUT_FORMAT}. Output directory: $OUTPUT_DIR"
}

main "$@"

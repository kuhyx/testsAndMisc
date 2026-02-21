#!/usr/bin/env bash

set -euo pipefail

# docx_to_pdf.sh
#
# Convert one or more DOCX files (or directories containing them) to PDF
# using LibreOffice.

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

OUTPUT_DIR=""
RECURSIVE=false
MERGE=false
MERGE_NAME="merged.pdf"
PRINT=false
DOCX_FILES=()

usage() {
  cat << EOF
Usage:
  $(basename "$0") [OPTIONS] PATH [PATH...]

Convert DOCX files to PDF using LibreOffice.
PATH can be a DOCX file or a directory containing DOCX files.

Options:
  -o DIR    Output directory (default: same as input)
  -m NAME   Merge all PDFs into one file (default: merged.pdf)
  -p        Print the merged PDF (requires -m)
  -r        Search directories recursively for DOCX files
  -h        Show this help

Examples:
  $(basename "$0") file.docx
  $(basename "$0") -o out file1.docx file2.docx
  $(basename "$0") /path/to/docs/
  $(basename "$0") -m merged.pdf /path/to/docs/
  $(basename "$0") -m combined.pdf -p /path/to/docs/
  $(basename "$0") -r -o out /path/to/docs/
EOF
}

ensure_libreoffice() {
  if ! command -v libreoffice > /dev/null 2>&1; then
    echo "Error: 'libreoffice' is not installed or not in PATH." >&2
    echo "Install it with: sudo pacman -S libreoffice-fresh  (Arch)" >&2
    echo "                 sudo apt install libreoffice       (Debian/Ubuntu)" >&2
    exit 1
  fi
}

ensure_pdfunite() {
  if ! command -v pdfunite > /dev/null 2>&1; then
    echo "Error: 'pdfunite' is not installed or not in PATH." >&2
    echo "Install it with: sudo pacman -S poppler  (Arch)" >&2
    echo "                 sudo apt install poppler-utils  (Debian/Ubuntu)" >&2
    exit 1
  fi
}

parse_args() {
  local opt
  OUTPUT_DIR=""
  DOCX_FILES=()

  while getopts ":o:m:prh" opt; do
    case "$opt" in
      o)
        OUTPUT_DIR="$OPTARG"
        ;;
      m)
        MERGE=true
        MERGE_NAME="$OPTARG"
        ;;
      p)
        PRINT=true
        ;;
      r)
        RECURSIVE=true
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
    echo "Error: at least one DOCX file or directory must be specified." >&2
    usage
    exit 1
  fi

  local arg
  local input_dir=""
  for arg in "$@"; do
    if [[ -d $arg ]]; then
      collect_from_dir "$arg"
      input_dir="$arg"
    else
      DOCX_FILES+=("$arg")
    fi
  done

  if [[ ${#DOCX_FILES[@]} -eq 0 ]]; then
    echo "Error: no DOCX files found." >&2
    exit 1
  fi

  if [[ -z ${OUTPUT_DIR:-} ]]; then
    if [[ -n $input_dir ]]; then
      OUTPUT_DIR="$input_dir"
    else
      OUTPUT_DIR="$(dirname "${DOCX_FILES[0]}")"
    fi
  fi

  if [[ ! -d $OUTPUT_DIR ]]; then
    mkdir -p "$OUTPUT_DIR"
  fi
}

collect_from_dir() {
  local dir="$1"
  local found

  if [[ $RECURSIVE == true ]]; then
    while IFS= read -r -d '' found; do
      DOCX_FILES+=("$found")
    done < <(find "$dir" -type f -iname '*.docx' -print0 | sort -z)
  else
    for found in "$dir"/*.docx "$dir"/*.DOCX; do
      if [[ -f $found ]]; then
        DOCX_FILES+=("$found")
      fi
    done
  fi
}

convert_docx() {
  local docx_file="$1"

  log "Converting '$docx_file' to PDF -> ${OUTPUT_DIR}/"
  libreoffice --headless --convert-to pdf --outdir "$OUTPUT_DIR" "$docx_file"
}

main() {
  ensure_libreoffice
  parse_args "$@"

  if [[ $MERGE == true ]]; then
    ensure_pdfunite
  fi

  if [[ $PRINT == true && $MERGE != true ]]; then
    echo "Error: -p (print) requires -m (merge)." >&2
    exit 1
  fi

  local docx
  local pdf_files=()
  for docx in "${DOCX_FILES[@]}"; do
    if [[ ! -f $docx ]]; then
      echo "Warning: '$docx' is not a regular file, skipping." >&2
      continue
    fi

    convert_docx "$docx"

    local base
    base="$(basename "${docx%.*}").pdf"
    pdf_files+=("${OUTPUT_DIR%/}/$base")
  done

  if [[ $MERGE == true && ${#pdf_files[@]} -gt 0 ]]; then
    local merged_path="${OUTPUT_DIR%/}/${MERGE_NAME}"
    log "Merging ${#pdf_files[@]} PDFs into '$merged_path'"
    pdfunite "${pdf_files[@]}" "$merged_path"
    log "Merged PDF created: $merged_path"

    if [[ $PRINT == true ]]; then
      log "Sending '$merged_path' to printer"
      lp "$merged_path"
    fi
  fi

  log "Done converting DOCX files to PDF. Output directory: $OUTPUT_DIR"
}

main "$@"

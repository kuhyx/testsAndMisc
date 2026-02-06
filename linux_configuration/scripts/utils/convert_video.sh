#!/usr/bin/env bash

set -euo pipefail

# convert_video.sh
#
# Convert video files to a target format (mp4 or webm) using ffmpeg.
# Accepts either a single video file or a directory (will recurse into subdirectories).

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Default settings
TARGET_FORMAT="mp4"
CRF="" # Will be set based on format if not specified
PRESET="medium"
DELETE_ORIGINAL=false
TARGET_PATH=""

# Video extensions to search for
ALL_VIDEO_EXTENSIONS=("mp4" "webm" "mkv" "avi" "mov" "wmv" "flv" "m4v" "mpg" "mpeg" "3gp" "ogv" "ts" "mts" "m2ts" "vob" "asf" "rm" "rmvb" "divx" "f4v")

usage() {
  cat << EOF
Usage:
  $(basename "$0") [OPTIONS] PATH

Convert video files to mp4 or webm format using ffmpeg.
PATH can be a single video file or a directory (will recurse into subdirectories).

Options:
  -f FORMAT    Target format: mp4 or webm (default: mp4)
  -c CRF       Quality level (default: 23 for mp4, 30 for webm; lower = better)
  -p PRESET    Encoding preset (default: medium)
               Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
  -d           Delete original file after successful conversion
  -h           Show this help

Examples:
  $(basename "$0") video.webm                    # Convert to mp4
  $(basename "$0") -f webm video.mp4             # Convert to webm
  $(basename "$0") /path/to/videos/              # Convert all videos in directory to mp4
  $(basename "$0") -f webm -c 25 -d /path/to/videos/
EOF
}

ensure_ffmpeg() {
  if ! command -v ffmpeg > /dev/null 2>&1; then
    echo "Error: 'ffmpeg' is not installed or not in PATH." >&2
    exit 1
  fi
}

get_video_extensions_except() {
  local exclude="$1"
  local exts=()
  for ext in "${ALL_VIDEO_EXTENSIONS[@]}"; do
    if [[ ${ext,,} != "${exclude,,}" ]]; then
      exts+=("$ext")
    fi
  done
  echo "${exts[@]}"
}

is_video_file() {
  local file="$1"
  local ext="${file##*.}"
  ext="${ext,,}" # lowercase

  for video_ext in "${ALL_VIDEO_EXTENSIONS[@]}"; do
    if [[ $ext == "${video_ext,,}" ]]; then
      return 0
    fi
  done
  return 1
}

convert_video() {
  local input_file="$1"
  local output_file="${input_file%.*}.${TARGET_FORMAT}"

  # Skip if output already exists
  if [[ -f $output_file ]]; then
    log "Skipping '$input_file': output '$output_file' already exists"
    return 0
  fi

  log "Converting '$input_file' -> '$output_file'"

  local ffmpeg_args=()
  ffmpeg_args+=(-hide_banner -loglevel warning -i "$input_file")

  if [[ $TARGET_FORMAT == "mp4" ]]; then
    # H.264 codec for video and AAC for audio (maximum compatibility)
    ffmpeg_args+=(-c:v libx264 -crf "$CRF" -preset "$PRESET")
    ffmpeg_args+=(-c:a aac -b:a 192k)
    ffmpeg_args+=(-movflags +faststart)
  elif [[ $TARGET_FORMAT == "webm" ]]; then
    # VP9 codec for video and Opus for audio
    ffmpeg_args+=(-c:v libvpx-vp9 -crf "$CRF" -b:v 0)
    ffmpeg_args+=(-c:a libopus -b:a 128k)
  fi

  ffmpeg_args+=("$output_file")

  if ffmpeg "${ffmpeg_args[@]}"; then
    log "Successfully converted '$input_file'"

    if [[ $DELETE_ORIGINAL == true ]]; then
      log "Deleting original: '$input_file'"
      rm "$input_file"
    fi
  else
    log "Error converting '$input_file'"
    [[ -f $output_file ]] && rm "$output_file"
    return 1
  fi
}

process_directory() {
  local dir="$1"
  local count=0
  local failed=0

  log "Searching for video files in '$dir'..."

  # Build find command dynamically
  local find_args=(-type f \()
  local first=true
  for ext in "${ALL_VIDEO_EXTENSIONS[@]}"; do
    if [[ ${ext,,} != "${TARGET_FORMAT,,}" ]]; then
      if [[ $first == true ]]; then
        first=false
      else
        find_args+=(-o)
      fi
      find_args+=(-iname "*.$ext")
    fi
  done
  find_args+=(\) -print0)

  while IFS= read -r -d '' file; do
    ((count++)) || true
    if ! convert_video "$file"; then
      ((failed++)) || true
    fi
  done < <(find "$dir" "${find_args[@]}" 2> /dev/null)

  log "Processed $count video file(s), $failed failed"

  if [[ $count -eq 0 ]]; then
    log "No video files found in '$dir'"
  fi
}

parse_args() {
  while getopts ":f:c:p:dh" opt; do
    case "$opt" in
      f)
        TARGET_FORMAT="${OPTARG,,}"
        if [[ $TARGET_FORMAT != "mp4" && $TARGET_FORMAT != "webm" ]]; then
          echo "Error: Format must be 'mp4' or 'webm'" >&2
          exit 1
        fi
        ;;
      c) CRF="$OPTARG" ;;
      p) PRESET="$OPTARG" ;;
      d) DELETE_ORIGINAL=true ;;
      h)
        usage
        exit 0
        ;;
      :)
        echo "Error: Option -$OPTARG requires an argument." >&2
        usage
        exit 1
        ;;
      \?)
        echo "Error: Invalid option -$OPTARG" >&2
        usage
        exit 1
        ;;
    esac
  done
  shift $((OPTIND - 1))

  if [[ $# -lt 1 ]]; then
    echo "Error: No path specified." >&2
    usage
    exit 1
  fi

  TARGET_PATH="$1"

  # Set default CRF based on format if not specified
  if [[ -z $CRF ]]; then
    if [[ $TARGET_FORMAT == "mp4" ]]; then
      CRF=23
    else
      CRF=30
    fi
  fi
}

main() {
  ensure_ffmpeg
  parse_args "$@"

  if [[ ! -e $TARGET_PATH ]]; then
    echo "Error: Path '$TARGET_PATH' does not exist." >&2
    exit 1
  fi

  if [[ -f $TARGET_PATH ]]; then
    # Single file
    if [[ ${TARGET_PATH,,} == *."$TARGET_FORMAT" ]]; then
      log "File '$TARGET_PATH' is already in $TARGET_FORMAT format, skipping."
      exit 0
    fi

    if is_video_file "$TARGET_PATH"; then
      convert_video "$TARGET_PATH"
    else
      echo "Error: '$TARGET_PATH' is not a recognized video file." >&2
      exit 1
    fi
  elif [[ -d $TARGET_PATH ]]; then
    process_directory "$TARGET_PATH"
  else
    echo "Error: '$TARGET_PATH' is neither a file nor a directory." >&2
    exit 1
  fi

  log "Done!"
}

main "$@"

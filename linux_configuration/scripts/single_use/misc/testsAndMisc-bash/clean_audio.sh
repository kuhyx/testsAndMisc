#!/usr/bin/env bash

set -euo pipefail

# clean_audio.sh — Fully automatic audio cleaner for speech (ASR-friendly)
#
# - Default preset is tuned for ASR (faster-whisper):
#   mono, 16 kHz, high-pass filter, denoise (RNNoise arnndn by default if model found/provided; else afftdn),
#   peak limiting to -0.5 dBFS. No aggressive gating/compression by default.
# - Optional "podcast" preset adds gentle dynamics and loudness leveling.
# - Accepts single files or directories (recursively).
# - Optional parallel processing.
#
# Dependencies: ffmpeg (arnndn filter recommended for best results)
# Optional: an RNNoise model file for arnndn (auto-discovered if present; otherwise falls back to afftdn)
#
# Usage examples:
#   Bash/clean_audio.sh input.wav                      # -> input_clean.wav (same folder)
#   Bash/clean_audio.sh input.wav -O out_dir           # -> out_dir/input_clean.wav
#   Bash/clean_audio.sh input_dir -O cleaned/ -j 4     # -> processes all audio files in dir
#   Bash/clean_audio.sh input.wav -m models/rn.nn      # -> use RNNoise model
#   Bash/clean_audio.sh input.wav --preset podcast     # -> add dynamics leveler
#

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

print_usage() {
  cat << EOF
Usage: $0 <input-file|input-dir> [options]

Options:
  -O, --out-dir DIR         Output directory (default: alongside input file).
  -e, --ext EXT             Output extension/container: wav|flac (default: wav).
  -m, --model PATH          RNNoise model file for arnndn; required by default unless --allow-fallback.
    --no-ml               Do not use arnndn even if model is provided (requires --allow-fallback).
      --preset NAME         asr (default) | podcast | aggressive
  -j, --jobs N              Parallel jobs for directory mode (default: 1).
  -f, --force               Overwrite outputs if they exist (ffmpeg -y).
  -q, --quiet               Reduce ffmpeg logging noise.
      --lowpass FREQ        Optional low-pass cutoff (e.g., 8000). Disabled by default.
      --suffix SUF          Suffix for output basename (default: _clean).
  -h, --help                Show this help.

Notes:
  - Default sample rate is 16 kHz mono PCM 16-bit (good for most speech ASR models).
  - If arnndn (RNNoise) is used, it usually outperforms afftdn for speech denoise.
  - The 'podcast' preset adds gentle dynamics and loudness normalization (single-pass).
EOF
}

require_cmd() {
  command -v "$1" > /dev/null 2>&1 || {
    echo "Error: Required command '$1' not found in PATH" >&2
    exit 1
  }
}

# Defaults
OUT_DIR=""
OUT_EXT="wav"
RN_MODEL=""
NO_ML=false
REQUIRE_ML=true # default: require RNNoise; install/guide if missing; fail fast if unavailable
PRESET="asr"
JOBS=1
FORCE=false
QUIET=false
LOWPASS=""
SUFFIX="_clean"
HIGHPASS="80"
AFFTDN_NF="-25"   # noise floor in dB for afftdn
AFFTDN_MD="8"     # mode for afftdn (higher can be more aggressive); requires builds that support 'md'
NO_ADVANCED=false # when true, avoid advanced options that some ffmpeg builds lack

# Parse args
if [[ $# -lt 1 ]]; then
  print_usage
  exit 1
fi

INPUT_PATH="$1"
shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -O | --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    -e | --ext)
      OUT_EXT="$2"
      shift 2
      ;;
    -m | --model)
      RN_MODEL="$2"
      shift 2
      ;;
    --no-ml)
      NO_ML=true
      shift
      ;;
    --preset)
      PRESET="$2"
      shift 2
      ;;
    -j | --jobs)
      JOBS="$2"
      shift 2
      ;;
    -f | --force)
      FORCE=true
      shift
      ;;
    -q | --quiet)
      QUIET=true
      shift
      ;;
    --lowpass)
      LOWPASS="$2"
      shift 2
      ;;
    --suffix)
      SUFFIX="$2"
      shift 2
      ;;
    --no-advanced | --compat)
      NO_ADVANCED=true
      shift
      ;;
    --allow-fallback)
      REQUIRE_ML=false
      shift
      ;;
    -h | --help)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      print_usage
      exit 1
      ;;
  esac
done

require_cmd ffmpeg

# Resolve FFmpeg binary (env override -> local build -> system)
FFMPEG_BIN=${FFMPEG_BIN:-}
if [[ -z ${FFMPEG_BIN} ]]; then
  if [[ -x "$SCRIPT_DIR/ffmpeg-build/FFmpeg/ffmpeg" ]]; then
    FFMPEG_BIN="$SCRIPT_DIR/ffmpeg-build/FFmpeg/ffmpeg"
  else
    FFMPEG_BIN="ffmpeg"
  fi
fi

if ! command -v "$FFMPEG_BIN" > /dev/null 2>&1 && [[ ! -x $FFMPEG_BIN ]]; then
  echo "Error: FFmpeg binary not found: $FFMPEG_BIN" >&2
  exit 1
fi
if ! $QUIET; then
  echo "Using FFmpeg binary: $FFMPEG_BIN" >&2
fi

FFMPEG_LOG=(-hide_banner)
if $QUIET; then
  FFMPEG_LOG+=(-loglevel error)
else
  FFMPEG_LOG+=(-loglevel info)
fi

FFMPEG_OVERWRITE=(-n)
if $FORCE; then
  FFMPEG_OVERWRITE=(-y)
fi

arnndn_available=false
if "$FFMPEG_BIN" -hide_banner -h filter=arnndn > /dev/null 2>&1; then
  arnndn_available=true
else
  if "$FFMPEG_BIN" -hide_banner -filters 2> /dev/null | grep -Eq '(^|[[:space:]])arnndn([[:space:]]|$)'; then
    arnndn_available=true
  fi
fi
if ! $QUIET; then
  echo "arnndn_available=$arnndn_available" >&2
fi

# Check if afftdn supports 'md' option
afftdn_supports_md=false
if "$FFMPEG_BIN" -hide_banner -h filter=afftdn 2> /dev/null | grep -q " md="; then
  afftdn_supports_md=true
fi

# Try to auto-discover an RNNoise model if none provided
find_default_rn_model() {
  # local candidate reserved for future selection logic
  # Allow env variable override
  if [[ -n ${RNNOISE_MODEL:-} && -f ${RNNOISE_MODEL} ]]; then
    echo "${RNNOISE_MODEL}"
    return 0
  fi
  local dirs=(
    "$SCRIPT_DIR/models"
    "$SCRIPT_DIR/../models"
    "/usr/share/rnnoise"
    "/usr/local/share/rnnoise"
    "/usr/share/ffmpeg/models"
    "$HOME/.local/share/rnnoise"
  )
  # Prefer '.rnnn' models (rnnoise-nu style) over legacy '.nn'
  local exts=("rnnn" "nn" "model")
  for d in "${dirs[@]}"; do
    if [[ -d $d ]]; then
      for ext in "${exts[@]}"; do
        # Pick the first matching model file
        for f in "$d"/*."$ext"; do
          if [[ -f $f ]]; then
            echo "$f"
            return 0
          fi
        done
      done
    fi
  done
  return 1
}

use_arnndn=false
if [[ $NO_ML == false ]]; then
  if [[ $arnndn_available == false ]]; then
    if $REQUIRE_ML; then
      echo "Error: FFmpeg 'arnndn' filter not available. Please install/upgrade FFmpeg with librnnoise (see Bash/install_ffmpeg_with_arnndn.sh)." >&2
      exit 9
    fi
  else
    # arnndn available; require an external model
    if [[ -n $RN_MODEL && -f $RN_MODEL ]]; then
      :
    else
      if model_path=$(find_default_rn_model); then
        RN_MODEL="$model_path"
      else
        if [[ -x "$SCRIPT_DIR/get_rnnoise_model.sh" ]]; then
          RN_TARGET_DIR="$SCRIPT_DIR/models" RN_TARGET_NAME="rnnoise_model.rnnn" "$SCRIPT_DIR/get_rnnoise_model.sh" --yes || true
          if model_path=$(find_default_rn_model); then
            RN_MODEL="$model_path"
          fi
        fi
      fi
    fi
    if [[ -z $RN_MODEL ]]; then
      echo "Error: RNNoise model required but not found. Automatic download failed." >&2
      echo "Hint: Set RN_URL to a reachable model URL and run Bash/get_rnnoise_model.sh, or supply -m /path/to/model.nn." >&2
      exit 10
    fi
    use_arnndn=true
    echo "Using RNNoise external model: $RN_MODEL" >&2
  fi
fi

build_filters() {
  local filters=()
  # Remove low-frequency rumble typical for handheld/room noise
  filters+=("highpass=f=${HIGHPASS}")

  # Denoise
  if $use_arnndn; then
    # arnndn with full mix keeps the model output; if no external model, rely on built-in
    filters+=("aresample=48000")
    filters+=("arnndn=m=${RN_MODEL}:mix=1.0")
  else
    # afftdn: FFT-based denoise, tune nf (noise floor) as needed
    if $REQUIRE_ML; then
      echo "Error: RNNoise required but not in use; aborting rather than falling back to afftdn. Use --allow-fallback to permit." >&2
      exit 11
    fi
    if $NO_ADVANCED; then
      filters+=("afftdn=nf=${AFFTDN_NF}")
    else
      if $afftdn_supports_md; then
        filters+=("afftdn=nf=${AFFTDN_NF}:md=${AFFTDN_MD}")
      else
        echo "Error: Your ffmpeg's afftdn filter does not support 'md='." >&2
        echo "Hint: Install/upgrade ffmpeg to a build that supports afftdn md or rerun with --no-advanced." >&2
        echo "      On Debian/Ubuntu you may need a newer ffmpeg from a PPA or build from source." >&2
        exit 8
      fi
    fi
  fi

  # Optional low-pass to shave hiss; keep disabled unless requested
  if [[ -n $LOWPASS ]]; then
    filters+=("lowpass=f=${LOWPASS}")
  fi

  case "$PRESET" in
    asr)
      # ASR-friendly: avoid heavy gating/leveling, just prevent clipping
      filters+=("alimiter=limit=0.94")
      ;;
    podcast)
      # Gentle dynamic normalization and broadcast-ish loudness (single-pass)
      # Note: single-pass loudnorm is approximate but OK for quick workflows
      filters+=("dynaudnorm=f=500:g=5:p=0.1")
      filters+=("loudnorm=i=-18:lra=9:tp=-2.0")
      ;;
    aggressive)
      # Heavier clean-up; may harm ASR slightly but suppress background more
      filters+=("agate=threshold=0.012:ratio=2.5:release=200")
      filters+=("dynaudnorm=f=400:g=7:p=0.1")
      filters+=("loudnorm=i=-18:lra=9:tp=-2.0")
      ;;
    *) ;;
  esac

  # Resample and format at the end for ASR
  filters+=("aresample=16000")
  filters+=("aformat=channel_layouts=mono:sample_fmts=s16")

  local IFS=","
  echo "${filters[*]}"
}

make_out_path_for_file() {
  local in_file="$1"
  local base
  base=$(basename -- "$in_file")
  base="${base%.*}"
  local out_base="${base}${SUFFIX}.${OUT_EXT}"
  if [[ -n $OUT_DIR ]]; then
    mkdir -p -- "$OUT_DIR"
    echo "$OUT_DIR/$out_base"
  else
    local dir
    dir=$(dirname -- "$in_file")
    echo "$dir/$out_base"
  fi
}

process_one() {
  local in_file="$1"
  local out_file
  out_file=$(make_out_path_for_file "$in_file")

  # Choose codec based on extension
  local codec=(-c:a pcm_s16le)
  if [[ $OUT_EXT == "flac" ]]; then
    codec=(-c:a flac)
  fi

  local af
  af=$(build_filters)

  if [[ -f $out_file && $FORCE == false ]]; then
    echo "Skip (exists): $out_file"
    return 0
  fi

  echo "Cleaning: $in_file -> $out_file"
  "$FFMPEG_BIN" "${FFMPEG_LOG[@]}" "${FFMPEG_OVERWRITE[@]}" -i "$in_file" -af "$af" "${codec[@]}" "$out_file"
}

# Concurrency helpers (bash >= 5 supports wait -n; fallback to sequential if not)
supports_wait_n=false
if [[ -n ${BASH_VERSINFO:-} && ${BASH_VERSINFO[0]} -ge 5 ]]; then
  supports_wait_n=true
fi

run_dir() {
  local dir="$1"
  # Common audio extensions (case-insensitive)
  mapfile -d '' files < <(find "$dir" -type f \
    \( -iname "*.wav" -o -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.flac" \
    -o -iname "*.ogg" -o -iname "*.opus" -o -iname "*.wma" -o -iname "*.webm" \) -print0)

  if [[ ${#files[@]} -eq 0 ]]; then
    echo "No audio files found in: $dir"
    return 0
  fi

  local running=0
  for f in "${files[@]}"; do
    if [[ $JOBS -le 1 || $supports_wait_n == false ]]; then
      process_one "$f"
    else
      process_one "$f" &
      ((running++))
      if ((running >= JOBS)); then
        wait -n || true
        ((running--))
      fi
    fi
  done

  # Wait for any remaining background jobs
  if ((JOBS > 1)) && $supports_wait_n; then
    wait || true
  fi
}

main() {
  # Sanity checks and notices
  if [[ -n $RN_MODEL && $use_arnndn == false && $NO_ML == false ]]; then
    echo "Note: arnndn filter not available in your ffmpeg or model missing — using afftdn." >&2
  fi

  if [[ -f $INPUT_PATH ]]; then
    process_one "$INPUT_PATH"
  elif [[ -d $INPUT_PATH ]]; then
    run_dir "$INPUT_PATH"
  else
    echo "Error: Input path not found: $INPUT_PATH" >&2
    exit 1
  fi
}

main "$@"

#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=lib/clean_audio_filters.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/clean_audio_filters.sh"

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




# Concurrency helpers (bash >= 5 supports wait -n; fallback to sequential if not)
supports_wait_n=false
if [[ -n ${BASH_VERSINFO:-} && ${BASH_VERSINFO[0]} -ge 5 ]]; then
  supports_wait_n=true
fi


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

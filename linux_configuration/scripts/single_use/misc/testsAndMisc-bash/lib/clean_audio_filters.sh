#!/usr/bin/env bash
# Usage text, dependency checks, ffmpeg filter construction and per-file
# processing for clean_audio.sh.
#
# Sourced by the entry script, which owns argument parsing and the run flow.
#
# The entry script probes ffmpeg once and sets these before calling
# build_filters. Declaring them here makes that contract explicit and keeps
# the static checker able to see it across the file boundary.
declare use_arnndn afftdn_supports_md supports_wait_n

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

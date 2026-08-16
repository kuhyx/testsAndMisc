#!/usr/bin/env bash
set -euo pipefail

# Transcribe an audio file using faster-whisper with automatic setup.
# - Creates Python venv in .venv
# - Installs ffmpeg and espeak-ng (best-effort) for test audio generation
# - Installs faster-whisper (and CUDA stack if NVIDIA is present)
# - Runs tools/transcribe_fw.py to produce .txt and .srt next to the input

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
TOOLS_DIR="$PROJECT_DIR/tools"
PY_RUNNER="$TOOLS_DIR/transcribe_fw.py"
PY_HELPERS="$TOOLS_DIR/transcribe_helpers.py"
VENV_DIR="$PROJECT_DIR/.venv"

usage() {
  cat << USAGE
Usage: $(basename "$0") [--online] [--prepare-model NAME --model-dir DIR] [-m model] [-l lang] [-o outdir] [audio_file]

Options:
	--online              Allow network to install deps and/or download models (default: offline)
	--prepare-model NAME  Download a model for offline use (implies --online)
	--model-dir DIR       Directory to store or load local models (default: ./models)
	-m model              Model size or path (tiny, base, small, medium, large-v3, etc.). Default: large-v3
	-l lang               Language code (e.g., en). Default: auto-detect
	-o outdir             Output directory (default: alongside input)
	[env] FW_DIARIZE=1    Enable diarization (speaker labels). Optional: FW_NUM_SPEAKERS=N. When --online, installs soundfile, speechbrain, and CPU-only torch/torchaudio.
	-h                    Show help
USAGE
}

log() {
  echo "[$(date +'%H:%M:%S')]" "$@"
}

# shellcheck source=lib/transcribe_pkgmgr.sh
source "$SCRIPT_DIR/lib/transcribe_pkgmgr.sh"
# shellcheck source=lib/transcribe_deps.sh
source "$SCRIPT_DIR/lib/transcribe_deps.sh"
# shellcheck source=lib/transcribe_venv.sh
source "$SCRIPT_DIR/lib/transcribe_venv.sh"

main() {
  # Defaults
  OFFLINE=1
  PREPARE_MODEL=""
  MODEL_DIR="$PROJECT_DIR/models"
  MODEL="large-v3"
  LANGUAGE=""
  OUTDIR=""
  INPUT_FILE=""

  # Parse args
  PARSED=$(getopt -o m:l:o:h -l online,prepare-model:,model-dir: -- "$@") || {
    usage
    exit 2
  }
  eval set -- "$PARSED"
  while true; do
    case "$1" in
      -m)
        MODEL="$2"
        shift 2
        ;;
      -l)
        LANGUAGE="$2"
        shift 2
        ;;
      -o)
        OUTDIR="$2"
        shift 2
        ;;
      -h)
        usage
        exit 0
        ;;
      --online)
        OFFLINE=0
        shift
        ;;
      --prepare-model)
        PREPARE_MODEL="$2"
        OFFLINE=0
        shift 2
        ;;
      --model-dir)
        MODEL_DIR="$2"
        shift 2
        ;;
      --)
        shift
        break
        ;;
      *) break ;;
    esac
  done
  INPUT_FILE="${1:-}"

  if [[ $OFFLINE -eq 1 ]]; then
    export HF_HUB_OFFLINE=1
    export TRANSFORMERS_OFFLINE=1
  fi

  install_system_deps
  setup_venv

  # If asked to prepare a model, do that and exit
  if [[ -n $PREPARE_MODEL ]]; then
    if [[ $OFFLINE -eq 1 ]]; then
      echo "--prepare-model requires network; rerun with --online." >&2
      exit 2
    fi
    install_python_deps 0
    prepare_model "$PREPARE_MODEL"
    log "Model '$PREPARE_MODEL' downloaded to $MODEL_DIR"
    exit 0
  fi

  # Detect NVIDIA GPU and enforce CUDA if present
  has_nvidia=0
  if command -v nvidia-smi > /dev/null 2>&1 && nvidia-smi -L > /dev/null 2>&1; then
    has_nvidia=1
  fi
  install_python_deps "$has_nvidia"
  ensure_runner

  local input="$INPUT_FILE"
  if [[ -z $input ]]; then
    input="$(generate_test_audio)"
    if [[ ! -s $input ]]; then
      echo "Failed to generate test audio. Please provide an audio file." >&2
      exit 4
    fi
  fi

  if [[ ! -f $input ]]; then
    echo "Input file not found: $input" >&2
    exit 2
  fi

  local args=("$input" "--model" "$MODEL")
  [[ -n $LANGUAGE ]] && args+=("--language" "$LANGUAGE")
  [[ -n $OUTDIR ]] && args+=("--outdir" "$OUTDIR")

  # Pass diarization via env if requested
  if [[ ${FW_DIARIZE:-} == "1" ]]; then
    args+=("--diarize")
    if [[ -n ${FW_NUM_SPEAKERS:-} ]]; then
      args+=("--num-speakers" "${FW_NUM_SPEAKERS}")
    fi
  fi

  if [[ $has_nvidia -eq 1 ]]; then
    ensure_cuda_runtime
    # Export common CUDA paths in case the env lacks them
    export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
    # Include system and possible venv-provided CUDA libs
    local pyver venv_cuda_paths=""
    if [[ -x "$VENV_DIR/bin/python" ]]; then
      pyver="$("$VENV_DIR"/bin/python "$PY_HELPERS" python-version 2> /dev/null || true)"
      if [[ -n $pyver ]]; then
        venv_cuda_paths="$VENV_DIR/lib/python$pyver/site-packages/nvidia/cublas/lib:$VENV_DIR/lib/python$pyver/site-packages/nvidia/cudnn/lib:$VENV_DIR/lib/python$pyver/site-packages/nvidia/cuda_runtime/lib"
      fi
    fi
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:${CUDA_HOME}/lib64:/usr/lib/x86_64-linux-gnu:/opt/cuda/lib64:/opt/cuda/targets/x86_64-linux/lib:${venv_cuda_paths}"
    export PATH="${PATH}:${CUDA_HOME}/bin"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    python "$PY_HELPERS" test-cuda || {
      echo "CUDA environment check failed. Aborting as requested." >&2
      exit 6
    }
    args+=("--device" "cuda")
  fi

  log "Transcribing: $input"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  if [[ $has_nvidia -eq 1 ]]; then
    if ! python "$PY_RUNNER" "${args[@]}"; then
      echo "CUDA execution requested due to detected NVIDIA GPU, but it failed. Aborting as requested (no CPU fallback)." >&2
      exit 6
    fi
  else
    # Offline: prefer local directory if present; otherwise use cache without network
    if [[ $OFFLINE -eq 1 ]]; then
      local local_model_path=""
      if [[ -d $MODEL ]]; then
        local_model_path="$MODEL"
      elif [[ -d "$MODEL_DIR/$MODEL" ]]; then
        local_model_path="$MODEL_DIR/$MODEL"
      fi
      if [[ -n $local_model_path ]]; then
        args=("$input" "--model" "$local_model_path")
        [[ -n $LANGUAGE ]] && args+=("--language" "$LANGUAGE")
        [[ -n $OUTDIR ]] && args+=("--outdir" "$OUTDIR")
      fi
    fi
    python "$PY_RUNNER" "${args[@]}"
  fi
}

main "$@"

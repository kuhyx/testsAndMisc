#!/bin/bash
# Virtualenv setup and the model download.
#
# Sourced by transcribe.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

setup_venv() {
  if [[ ! -d $VENV_DIR ]]; then
    log "Creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  if [[ $OFFLINE -eq 0 ]]; then
    python -m pip install --upgrade pip wheel setuptools
  fi
}

install_python_deps() {
  # Install deps; if NVIDIA GPU is present, prefer CUDA-capable stack (cu12)
  local has_nvidia_flag="${1:-0}"
  log "Installing faster-whisper and dependencies"
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  export PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT:-20}
  if [[ $OFFLINE -eq 1 ]]; then
    # Offline: do not install, just verify modules
    if ! python "$PY_HELPERS" check-faster-whisper; then
      exit 7
    fi
    # If diarization requested offline, check for its deps too (warn-only)
    if [[ ${FW_DIARIZE:-} == "1" ]]; then
      python "$PY_HELPERS" check-diarization || true
    fi
    return 0
  fi
  if [[ $has_nvidia_flag -eq 1 ]]; then
    # If ctranslate2 is not installed, attempt CUDA-enabled wheel (with fallback)
    if ! "$VENV_DIR/bin/python" "$PY_HELPERS" check-ctranslate2 2> /dev/null; then
      log "Installing CUDA-enabled CTranslate2 (cu12 wheel)"
      python -m pip install --progress-bar on --retries 1 --upgrade "ctranslate2<5,>=4.0" --extra-index-url https://download.opennmt.net/ctranslate2/cu12 ||
        log "Warning: could not reach cu12 wheel index; will proceed with available ctranslate2"
    fi
    # Ensure NVIDIA CUDA 12 runtime libs are available inside the venv
    python -m pip install --progress-bar on --retries 1 --upgrade nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 ||
      log "Warning: failed to install NVIDIA cu12 runtime libs via pip"
  fi
  python -m pip install --progress-bar on --retries 1 --upgrade faster-whisper ffmpeg-python

  # If diarization requested and online, install its Python deps best-effort
  if [[ ${FW_DIARIZE:-} == "1" ]]; then
    python -m pip install --progress-bar on --retries 1 --upgrade soundfile speechbrain ||
      log "Warning: failed to install soundfile/speechbrain"
    # Torch and torchaudio CPU wheels (force to avoid mismatched CUDA builds)
    python -m pip install --progress-bar on --retries 1 --upgrade --force-reinstall --index-url https://download.pytorch.org/whl/cpu torch torchaudio ||
      log "Warning: failed to install torch/torchaudio CPU wheels"
  fi
  python "$PY_HELPERS" deps-installed
}

ensure_runner() {
  if [[ ! -f $PY_RUNNER ]]; then
    echo "Runner not found: $PY_RUNNER" >&2
    exit 3
  fi
}

generate_test_audio() {
  local tmpwav
  tmpwav="${PROJECT_DIR}/test_fw.wav"
  if command -v espeak-ng > /dev/null 2>&1; then
    log "Generating test audio via espeak-ng -> $tmpwav" >&2
    espeak-ng -w "$tmpwav" "This is a quick test of faster whisper transcription." > /dev/null 2>&1 || true
  fi
  # If espeak-ng failed or not present, try espeak
  if [[ ! -s $tmpwav ]] && command -v espeak > /dev/null 2>&1; then
    log "espeak-ng unavailable or failed; trying espeak -> $tmpwav" >&2
    espeak -w "$tmpwav" "This is a quick test of faster whisper transcription." > /dev/null 2>&1 || true
  fi
  # Fallback: generate tone via Python stdlib (no external deps)
  if [[ ! -s $tmpwav ]]; then
    log "Generating 3s 1kHz WAV via Python stdlib -> $tmpwav" >&2
    python3 "$PY_HELPERS" generate-wav --file "$tmpwav" || true
  fi
  # Final fallback: tone via ffmpeg
  if [[ ! -s $tmpwav ]]; then
    log "Creating a 3s sine tone WAV via ffmpeg -> $tmpwav" >&2
    ffmpeg -f lavfi -i sine=frequency=1000:duration=3 -ar 16000 -ac 1 -f wav -y "$tmpwav" > /dev/null 2>&1 || true
  fi
  echo "$tmpwav"
}

prepare_model() {
  # Download a model for offline use into MODEL_DIR
  local name="$1"
  mkdir -p "$MODEL_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  log "Preparing model '$name' into $MODEL_DIR"
  python "$PY_HELPERS" prepare-model --model "$name" --model-dir "$MODEL_DIR"
}

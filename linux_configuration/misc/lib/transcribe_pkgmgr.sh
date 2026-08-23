#!/bin/bash
# Package manager detection and CUDA runtime checks.
#
# Sourced by transcribe.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

detect_pkg_mgr() {
  if command -v apt-get > /dev/null 2>&1; then
    echo apt
    return
  fi
  if command -v dnf > /dev/null 2>&1; then
    echo dnf
    return
  fi
  if command -v yum > /dev/null 2>&1; then
    echo yum
    return
  fi
  if command -v pacman > /dev/null 2>&1; then
    echo pacman
    return
  fi
  if command -v zypper > /dev/null 2>&1; then
    echo zypper
    return
  fi
  echo none
}

has_libcublas12() {
  # Common system locations
  for d in \
    /usr/lib \
    /usr/lib64 \
    /usr/local/cuda/lib64 \
    /usr/local/cuda-12*/lib64 \
    /opt/cuda/lib64 \
    /opt/cuda/targets/x86_64-linux/lib; do
    if [[ -e "$d/libcublas.so.12" ]]; then
      return 0
    fi
  done
  # venv-provided NVIDIA CUDA libs
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    local pyver
    pyver="$("$VENV_DIR"/bin/python "$PY_HELPERS" python-version 2> /dev/null || true)"
    if [[ -n $pyver ]]; then
      for d in "$VENV_DIR/lib/python$pyver/site-packages/nvidia/cublas/lib" \
        "$VENV_DIR/lib/python$pyver/site-packages/nvidia/cudnn/lib" \
        "$VENV_DIR/lib/python$pyver/site-packages/nvidia/cuda_runtime/lib"; do
        if [[ -e "$d/libcublas.so.12" ]]; then
          return 0
        fi
      done
    fi
  fi
  return 1
}

ensure_cuda_runtime() {
  local mgr
  mgr="$(detect_pkg_mgr)"
  if [[ $OFFLINE -eq 1 ]]; then
    if has_libcublas12; then return 0; fi
    echo "CUDA runtime (libcublas.so.12) not found and offline mode is enabled. Install CUDA 12 runtime or rerun with --online." >&2
    exit 6
  fi
  if has_libcublas12; then
    return 0
  fi
  if ! command -v sudo > /dev/null 2>&1; then
    log "sudo not found; skipping CUDA runtime install attempt."
  else
    log "CUDA cuBLAS 12 not found; attempting to install CUDA runtime (manager: $mgr)"
    set +e
    case "$mgr" in
      pacman)
        sudo pacman -Sy --noconfirm cuda cudnn || true
        ;;
      apt)
        sudo apt-get update -y || true
        sudo apt-get install -y nvidia-cuda-toolkit || true
        ;;
      dnf | yum)
        sudo "$mgr" install -y cuda cudnn || true
        ;;
      zypper)
        sudo zypper install -y cuda cudnn || true
        ;;
      *) log "Unknown package manager; cannot install CUDA automatically." ;;
    esac
    set -e
  fi
  # Re-check
  if ! has_libcublas12; then
    echo "CUDA runtime (libcublas.so.12) not found after attempted install. Please install CUDA 12 toolkit/runtime and re-run." >&2
    exit 6
  fi
}

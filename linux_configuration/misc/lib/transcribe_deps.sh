#!/bin/bash
# System dependency and CUDA runtime installation.
#
# Sourced by transcribe.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

install_system_deps() {
  have_cmd() { command -v "$1" > /dev/null 2>&1; }
  local need_ffmpeg=0 need_espeak=0
  have_cmd ffmpeg || need_ffmpeg=1
  have_cmd espeak-ng || need_espeak=1

  # If diarization requested and online, we may also try to ensure libsndfile
  local need_libsndfile=0
  if [[ ${FW_DIARIZE:-} == "1" ]]; then
    # Heuristic: check common library file
    if [[ ! -e /usr/lib/x86_64-linux-gnu/libsndfile.so && ! -e /usr/lib/libsndfile.so && ! -e /usr/lib64/libsndfile.so ]]; then
      need_libsndfile=1
    fi
  fi

  if [[ $need_ffmpeg -eq 0 && $need_espeak -eq 0 && $need_libsndfile -eq 0 ]]; then
    log "System deps present: ffmpeg, espeak-ng${FW_DIARIZE:+, libsndfile}"
    return 0
  fi

  if [[ $OFFLINE -eq 1 ]]; then
    echo "Missing system dependencies (ffmpeg/espeak-ng) but running in offline mode. Install them or rerun with --online." >&2
    exit 5
  fi

  local mgr
  mgr="$(detect_pkg_mgr)"
  log "Detected package manager: $mgr (installing missing: $([[ $need_ffmpeg -eq 1 ]] && echo ffmpeg)$([[ $need_espeak -eq 1 ]] && echo espeak-ng)$([[ $need_libsndfile -eq 1 ]] && echo libsndfile))"

  if ! command -v sudo > /dev/null 2>&1; then
    log "sudo not found; skipping system package installation attempt."
    return 0
  fi

  # Avoid exiting on install errors; continue best-effort
  set +e
  case "$mgr" in
    apt)
      sudo apt-get update -y || log "apt-get update failed; continuing"
      pkgs=(python3-venv python3-pip)
      [[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
      [[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
      if [[ $need_libsndfile -eq 1 ]]; then
        # Try both names across releases
        pkgs+=(libsndfile1)
        sudo apt-get install -y libsndfile1 || true
        # If that failed, try libsndfile2 (newer distros)
        sudo apt-get install -y libsndfile2 || true
      fi
      sudo apt-get install -y "${pkgs[@]}" || log "apt-get install failed; continuing"
      ;;
    dnf)
      pkgs=(python3-venv python3-pip)
      [[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
      [[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
      [[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile)
      sudo dnf install -y "${pkgs[@]}" || log "dnf install failed; continuing"
      ;;
    yum)
      pkgs=(python3-venv python3-pip)
      [[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
      [[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
      [[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile)
      sudo yum install -y "${pkgs[@]}" || log "yum install failed; continuing"
      ;;
    pacman)
      pkgs=(python-virtualenv python-pip)
      [[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
      [[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
      [[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile)
      sudo pacman -Sy --noconfirm "${pkgs[@]}" || log "pacman install failed; continuing"
      ;;
    zypper)
      pkgs=(python311-virtualenv python311-pip)
      [[ $need_ffmpeg -eq 1 ]] && pkgs+=(ffmpeg)
      [[ $need_espeak -eq 1 ]] && pkgs+=(espeak-ng)
      [[ $need_libsndfile -eq 1 ]] && pkgs+=(libsndfile1)
      sudo zypper install -y "${pkgs[@]}" || log "zypper install failed; continuing"
      ;;
    *)
      log "Unknown package manager; please ensure ffmpeg and espeak-ng are installed."
      ;;
  esac
  set -e
}

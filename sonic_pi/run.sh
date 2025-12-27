#!/usr/bin/env bash

set -euo pipefail

# Headless Sonic Pi playback on Arch Linux only.
# - Installs Sonic Pi from AUR (sonic-pi.git) if missing
# - Starts the Sonic Pi server headlessly and evaluates the given .rb file
# - Optional: --duration N to auto-stop after N seconds

PATH="$HOME/.local/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRACK_FILE="$SCRIPT_DIR/chill_track.rb"
DURATION=""

require_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_arch_from_aur_git() {
  # Build and install from AUR using an AUR helper (handles recursive AUR deps)
  if [ "$EUID" -eq 0 ]; then
    echo "Do not run the AUR build as root. Re-run this script as a regular user." >&2
    return 1
  fi

  # Try AUR helpers first (they handle recursive AUR deps)
  if require_cmd yay; then
    echo "Installing Sonic Pi via yay..."
    yay -S --needed --noconfirm sonic-pi
    return $?
  elif require_cmd paru; then
    echo "Installing Sonic Pi via paru..."
    paru -S --needed --noconfirm sonic-pi
    return $?
  fi

  echo "No AUR helper found. Installing yay first..."
  sudo pacman -S --needed --noconfirm base-devel git || true
  local TMPDIR
  TMPDIR=$(mktemp -d -t yay-install-XXXXXX)
  (
    set -e
    cd "$TMPDIR"
    git clone https://aur.archlinux.org/yay.git
    cd yay
    makepkg -si --noconfirm
  )
  # Now use yay to install sonic-pi
  if require_cmd yay; then
    echo "Installing Sonic Pi via yay..."
    yay -S --needed --noconfirm sonic-pi
    return $?
  fi
  echo "Failed to install yay." >&2
  return 1
}

install_sonic_pi() {
  echo "Installing Sonic Pi (if missing)..."
  if require_cmd pacman; then
    if require_cmd sonic-pi; then
      echo "Sonic Pi is already installed."
      return 0
    fi
    install_arch_from_aur_git
    if ! require_cmd sonic-pi; then
      echo "Sonic Pi installation failed via AUR." >&2
      exit 1
    fi
  else
    echo "This installer only supports Arch Linux (pacman)." >&2
    exit 1
  fi
}

# No sonic-pi-tool or pip logic; headless playback uses the built-in REPL only.

find_repl() {
  REPL_BIN=""
  if [ -x "/opt/sonic-pi/bin/sonic-pi-repl.sh" ]; then
    REPL_BIN="/opt/sonic-pi/bin/sonic-pi-repl.sh"
  elif require_cmd sonic-pi-repl.sh; then
    REPL_BIN="$(command -v sonic-pi-repl.sh)"
  fi
}

# Ensure TRACK_FILE is an absolute path so REPL can always find it
resolve_track_file() {
  # If already absolute, keep as-is
  case "$TRACK_FILE" in
    /*) : ;;
    *)
      if require_cmd realpath; then
        TRACK_FILE="$(realpath -m "$TRACK_FILE")"
      elif require_cmd readlink; then
        # Some systems support -f
        TRACK_FILE="$(readlink -f "$TRACK_FILE" 2>/dev/null || printf "%s/%s" "$(cd "$(dirname "$TRACK_FILE")" && pwd)" "$(basename "$TRACK_FILE")")"
      else
        TRACK_FILE="$(cd "$(dirname "$TRACK_FILE")" && pwd)/$(basename "$TRACK_FILE")"
      fi
      ;;
  esac
}

# Start Sonic Pi headlessly using the built-in REPL only
headless_play() {
  find_repl
  if [ -n "$REPL_BIN" ]; then
    echo "Starting Sonic Pi REPL with track: $TRACK_FILE"
    if [ -n "$DURATION" ]; then
      "$REPL_BIN" "$TRACK_FILE" &
      REPL_PID=$!
      echo "REPL PID $REPL_PID; playing for $DURATION seconds..."
      sleep "$DURATION" || true
      echo "Stopping (TERM REPL to trigger graceful daemon exit)..."
      kill -TERM "$REPL_PID" || true
      wait "$REPL_PID" || true
    else
      exec "$REPL_BIN" "$TRACK_FILE"
    fi
    return 0
  fi

  echo "REPL script not found. Ensure Sonic Pi is installed from AUR (sonic-pi.git)." >&2
  exit 1
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [path/to/track.rb] [--duration SECONDS]

Defaults:
  track file $TRACK_FILE
  --duration  run until Ctrl+C
  (headless only)
EOF
}

parse_args() {
  local saw_file="false"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -d|--duration)
        DURATION="$2"; shift 2 ;;
      -h|--help)
        usage; exit 0 ;;
      --)
        shift; break ;;
      -*)
        echo "Unknown option: $1" >&2; usage; exit 1 ;;
      *)
        if [[ "$saw_file" == "false" ]]; then
          TRACK_FILE="$1"; saw_file="true"; shift
        else
          echo "Unexpected extra argument: $1" >&2; usage; exit 1
        fi
        ;;
    esac
  done
}

main() {
  parse_args "$@"
  if [ ! -f "$TRACK_FILE" ]; then
    echo "Track file not found: $TRACK_FILE" >&2
    exit 1
  fi
  resolve_track_file
  install_sonic_pi
  headless_play
}

main "$@"

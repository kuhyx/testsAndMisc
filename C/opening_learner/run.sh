#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Install SDL2 dev if sdl2-config is missing; otherwise build and run.

if ! command -v sdl2-config >/dev/null 2>&1; then
  echo "sdl2-config not found. Attempting to install SDL2 dev..."
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
      ubuntu|debian|linuxmint|neon|pop)
        sudo apt-get update
        sudo apt-get install -y libsdl2-dev
        ;;
      arch|manjaro|endeavouros)
        pacman -Q sdl2 &>/dev/null || sudo pacman -S --noconfirm sdl2
        ;;
      fedora)
        sudo dnf install -y SDL2-devel
        ;;
      opensuse*|sles)
        sudo zypper install -y libSDL2-devel
        ;;
      void)
        sudo xbps-install -Sy SDL2-devel
        ;;
      alpine)
        sudo apk add sdl2-dev
        ;;
      *)
        echo "Unsupported distro ($ID). Please install SDL2 dev manually and rerun." >&2
        exit 3
        ;;
    esac
  else
    echo "/etc/os-release not found; cannot auto-detect distro. Install SDL2 dev manually." >&2
    exit 3
  fi
fi

./check_build.sh
./opening_learner

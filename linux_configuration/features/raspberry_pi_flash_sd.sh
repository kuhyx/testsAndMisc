#!/bin/bash
# Raspberry Pi SD Card Flash Script
# This script flashes Raspberry Pi OS to an SD card (locally or on a remote laptop)
#
# Usage:
#   ./raspberry_pi_flash_sd.sh              - Flash SD card locally
#   ./raspberry_pi_flash_sd.sh remote       - Flash SD card on remote laptop via SSH

set -euo pipefail

# Script directory for config file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/.raspberry_pi.conf"

# Load configuration from gitignored config file if it exists
if [[ -f $CONFIG_FILE ]]; then
  # shellcheck source=/dev/null
  source "$CONFIG_FILE"
fi

# Configuration - Customize these values (or set in config file)
PI_HOSTNAME="${PI_HOSTNAME:-nextcloud-pi}"
PI_USER="${PI_USER:-pi}"
PI_PASSWORD="${PI_PASSWORD:-}"
PI_TIMEZONE="${PI_TIMEZONE:-Europe/Warsaw}"
SD_CARD_DEVICE="${SD_CARD_DEVICE:-}"

# Remote laptop configuration - will be auto-discovered if not set
REMOTE_LAPTOP_IP="${REMOTE_LAPTOP_IP:-}"
REMOTE_LAPTOP_USER="${REMOTE_LAPTOP_USER:-kuchy}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# All log functions output to stderr so they don't interfere with function return values
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
}

die() {
  log_error "$1"
  exit 1
}

check_root() {
  if [[ $EUID -ne 0 ]]; then
    die "This script must be run as root. Use: sudo $0"
  fi
}

save_config() {
  cat > "$CONFIG_FILE" << EOF
# Raspberry Pi Setup - Auto-generated config
# This file is gitignored and stores discovered settings

# Remote laptop (auto-discovered)
REMOTE_LAPTOP_IP="${REMOTE_LAPTOP_IP}"
REMOTE_LAPTOP_USER="${REMOTE_LAPTOP_USER}"

# Pi configuration
PI_HOSTNAME="${PI_HOSTNAME}"
PI_USER="${PI_USER}"
PI_TIMEZONE="${PI_TIMEZONE}"

# Generated passwords (KEEP THIS FILE SECURE!)
PI_PASSWORD="${PI_PASSWORD}"
EOF
  chmod 600 "$CONFIG_FILE"
  log_info "Configuration saved to $CONFIG_FILE"
}

generate_password() {
  local length="${1:-16}"
  local chars
  chars=$(dd if=/dev/urandom bs=256 count=1 2> /dev/null | tr -dc 'A-Za-z0-9!@#$%&*' | cut -c1-"$length")
  echo "$chars"
}

auto_generate_pi_password() {
  if [[ -z $PI_PASSWORD ]]; then
    PI_PASSWORD=$(generate_password 16)
    log_info "Auto-generated Pi password (will be saved to config file)"
  fi
}

# =============================================================================
# Network Discovery Functions
# =============================================================================

ensure_dependencies() {
  local missing_packages=()

  if ! command -v nmap &> /dev/null; then
    missing_packages+=("nmap")
  fi

  if ! command -v sshpass &> /dev/null; then
    missing_packages+=("sshpass")
  fi

  if [[ ${#missing_packages[@]} -gt 0 ]]; then
    log_info "Installing missing packages: ${missing_packages[*]}"

    if command -v pacman &> /dev/null; then
      sudo pacman -S --noconfirm "${missing_packages[@]}"
    elif command -v apt-get &> /dev/null; then
      sudo apt-get update && sudo apt-get install -y "${missing_packages[@]}"
    elif command -v dnf &> /dev/null; then
      sudo dnf install -y "${missing_packages[@]}"
    else
      die "Could not detect package manager. Please install manually: ${missing_packages[*]}"
    fi

    log_success "Dependencies installed"
  fi
}

# shellcheck source=lib/pi_flash_remote.sh
source "$SCRIPT_DIR/lib/pi_flash_remote.sh"
# shellcheck source=lib/pi_flash_image.sh
source "$SCRIPT_DIR/lib/pi_flash_image.sh"
# shellcheck source=lib/pi_flash_exec.sh
source "$SCRIPT_DIR/lib/pi_flash_exec.sh"


main() {
  local command="${1:-help}"

  case "$command" in
    local)
      phase_flash_local
      ;;
    remote)
      phase_flash_remote
      ;;
    execute-remote)
      phase_execute_remote "${2:-}"
      ;;
    help | --help | -h)
      show_help
      ;;
    *)
      log_error "Unknown command: $command"
      show_help
      exit 1
      ;;
  esac
}

main "$@"

#!/usr/bin/env bash

# Root BL9000 phone from Arch Linux
#
# This script automates the rooting process for BL9000 phones using Magisk.
# It handles:
# - Installing required dependencies (ADB, fastboot, boot image tools)
# - Detecting and connecting to the device
# - Unlocking the bootloader (with user confirmation)
# - Extracting boot image from device
# - Patching boot image with Magisk
# - Flashing patched boot image
#
# Prerequisites:
# - USB debugging must be enabled on the phone
# - OEM unlocking must be enabled in Developer Options
# - Phone should be charged to at least 50%
#
# Conventions: sudo re-exec, idempotent, log with timestamps, follow repo style

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
LOG_FILE="/var/log/bl9000-root.log"
WORK_DIR="${HOME}/.cache/bl9000-root"
MAGISK_APK_URL="https://github.com/topjohnwu/Magisk/releases/latest/download/Magisk.apk"
BOOT_IMG=""
PATCHED_BOOT_IMG=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

timestamp() { date '+%Y-%m-%d %H:%M:%S%z'; }

log() {
  local msg="$1"
  echo -e "${GREEN}[$(timestamp)]${NC} $msg"
  if [[ -w "$(dirname "$LOG_FILE")" ]] || [[ ! -e $LOG_FILE && -w /var/log ]]; then
    echo "[$(timestamp)] $msg" >> "$LOG_FILE" 2>&1 || true
  fi
}

warn() {
  local msg="$1"
  echo -e "${YELLOW}[WARN]${NC} $msg" >&2
  if [[ -w "$(dirname "$LOG_FILE")" ]] || [[ ! -e $LOG_FILE && -w /var/log ]]; then
    echo "[$(timestamp)] [WARN] $msg" >> "$LOG_FILE" 2>&1 || true
  fi
}

error() {
  local msg="$1"
  echo -e "${RED}[ERROR]${NC} $msg" >&2
  if [[ -w "$(dirname "$LOG_FILE")" ]] || [[ ! -e $LOG_FILE && -w /var/log ]]; then
    echo "[$(timestamp)] [ERROR] $msg" >> "$LOG_FILE" 2>&1 || true
  fi
}

die() {
  error "$1"
  exit 1
}

print_header() {
  echo
  echo -e "${BLUE}========================================${NC}"
  echo -e "${BLUE}  $1${NC}"
  echo -e "${BLUE}========================================${NC}"
  echo
}

confirm() {
  local prompt="$1"
  local reply
  read -r -p "$(echo -e "${YELLOW}${prompt}${NC} [y/N]: ")" reply
  case "$reply" in
    [Yy][Ee][Ss] | [Yy]) return 0 ;;
    *) return 1 ;;
  esac
}

require_non_root() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    die "Do not run this script as root. ADB must run as your regular user to access USB devices properly."
  fi
}

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/bl9000_usage.sh
source "$SCRIPT_DIR/lib/bl9000_usage.sh"
# shellcheck source=lib/bl9000_deps.sh
source "$SCRIPT_DIR/lib/bl9000_deps.sh"
# shellcheck source=lib/bl9000_backup.sh
source "$SCRIPT_DIR/lib/bl9000_backup.sh"
# shellcheck source=lib/bl9000_device.sh
source "$SCRIPT_DIR/lib/bl9000_device.sh"
# shellcheck source=lib/bl9000_mtkclient.sh
source "$SCRIPT_DIR/lib/bl9000_mtkclient.sh"
# shellcheck source=lib/bl9000_magisk.sh
source "$SCRIPT_DIR/lib/bl9000_magisk.sh"

main() {
  require_non_root

  # Create work directory
  mkdir -p "$WORK_DIR"

  local command="${1:-help}"
  shift || true

  # Handle flash command's image argument before option parsing
  if [[ $command == "flash" && -n ${1:-} && $1 != --* ]]; then
    PATCHED_BOOT_IMG="$1"
    if [[ ! -f $PATCHED_BOOT_IMG ]]; then
      die "Patched boot image file not found: $PATCHED_BOOT_IMG"
    fi
    shift
  fi

  # Parse options
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --work-dir)
        WORK_DIR="$2"
        mkdir -p "$WORK_DIR"
        shift 2
        ;;
      --boot-img)
        BOOT_IMG="$2"
        if [[ ! -f $BOOT_IMG ]]; then
          die "Boot image file not found: $BOOT_IMG"
        fi
        shift 2
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        error "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
  done

  case "$command" in
    install-deps)
      install_dependencies
      setup_udev_rules
      ;;
    install-mtk)
      install_dependencies
      setup_udev_rules
      install_mtkclient
      ;;
    check)
      check_device
      ;;
    backup)
      check_device || die "Device check failed"
      backup_device_data
      ;;
    unlock)
      check_device || die "Device check failed"
      unlock_bootloader
      ;;
    extract-mtk)
      extract_boot_with_mtkclient
      ;;
    patch)
      # Patch the extracted boot image with Magisk
      if [[ -f "$WORK_DIR/boot.img" ]]; then
        BOOT_IMG="$WORK_DIR/boot.img"
      fi
      patch_boot_with_magisk
      ;;
    flash)
      # Flash the patched boot image
      if [[ -z ${PATCHED_BOOT_IMG:-} ]]; then
        if [[ -f "$WORK_DIR/magisk_patched.img" ]]; then
          PATCHED_BOOT_IMG="$WORK_DIR/magisk_patched.img"
        else
          die "No patched boot image specified and none found at $WORK_DIR/magisk_patched.img"
        fi
      fi
      flash_patched_boot
      ;;
    auto-root)
      # Automated rooting: extract -> patch -> flash
      extract_boot_with_mtkclient || die "Boot extraction failed"
      BOOT_IMG="$WORK_DIR/boot.img"
      patch_boot_with_magisk || die "Boot patching failed"
      flash_patched_boot || die "Boot flashing failed"
      log "Rooting process completed!"
      ;;
    root)
      run_root_only
      ;;
    full)
      run_full_process
      ;;
    clean)
      clean_work_dir
      ;;
    help | --help | -h)
      usage
      ;;
    *)
      error "Unknown command: $command"
      usage
      exit 1
      ;;
  esac
}

main "$@"

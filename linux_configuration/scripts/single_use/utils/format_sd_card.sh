#!/usr/bin/env bash

set -euo pipefail

# format_sd_card.sh
#
# Safely detect and format an SD card.
#
# Defaults:
#   * Detect removable disks via lsblk (TYPE=disk, RM=1)
#   * Interactive selection if multiple candidates found
#   * Unmount all partitions before formatting
#   * Create a single partition and format it as exfat by default
#
# Usage:
#   sudo ./format_sd_card.sh              # interactive detection + confirmation
#   sudo ./format_sd_card.sh /dev/sdX     # format specific device
#   sudo ./format_sd_card.sh --dry-run    # show what would happen, no changes
#   sudo ./format_sd_card.sh --help

DRY_RUN=false
FILESYSTEM="exfat"   # you can change to ext4, vfat, etc.
DUMBPHONE_MODE=false # when true: MBR + ~30GiB FAT32 primary partition

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

usage() {
  cat << EOF
Usage: sudo $(basename "$0") [OPTIONS] [DEVICE]

Safely detect and format an SD card.

Options:
  --dry-run       Show actions without executing them
  --fs TYPE       Filesystem type (default: ${FILESYSTEM})
  --dumbphone     Use MBR and create a ~30GiB FAT32 partition for old phones
  -h, --help      Show this help

If DEVICE is not provided, removable disks are detected automatically and you
will be asked to pick one if multiple are found.

WARNING: This will ERASE ALL DATA on the selected device.
EOF
}

ensure_fs_tools() {
  case "$FILESYSTEM" in
    vfat | fat32)
      # Ensure mkfs.vfat is available
      if ! command -v mkfs.vfat > /dev/null 2>&1; then
        echo "mkfs.vfat not found. Attempting to install dosfstools..." >&2

        # Detect package manager
        if command -v pacman > /dev/null 2>&1; then
          run "pacman -Sy --needed --noconfirm dosfstools"
        elif command -v apt-get > /dev/null 2>&1; then
          run "apt-get update"
          run "apt-get install -y dosfstools"
        else
          echo "Unsupported package manager. Please install 'dosfstools' (provides mkfs.vfat) manually." >&2
          exit 1
        fi

        # Re-check
        if ! command -v mkfs.vfat > /dev/null 2>&1; then
          echo "mkfs.vfat is still not available after attempted installation." >&2
          exit 1
        fi
      fi
      ;;
    exfat)
      # exfat tools
      if ! command -v mkfs.exfat > /dev/null 2>&1; then
        echo "mkfs.exfat not found. Please install exfatprogs (Arch) or exfat-fuse/exfatprogs (Debian/Ubuntu)." >&2
        # Do not auto-install here to avoid too much magic across distros
        exit 1
      fi
      ;;
    ext4)
      if ! command -v mkfs.ext4 > /dev/null 2>&1; then
        echo "mkfs.ext4 not found. Please install e2fsprogs." >&2
        exit 1
      fi
      ;;
  esac
}

require_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
  fi
}

run() {
  if [[ $DRY_RUN == true ]]; then
    log "DRY RUN: $*"
  else
    log "RUN: $*"
    "$@"
  fi
}

confirm() {
  local prompt="$1"
  read -r -p "$prompt [y/N]: " ans
  case "$ans" in
    y | Y | yes | YES) return 0 ;;
    *) return 1 ;;
  esac
}

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/sd_card_ops.sh
source "$SCRIPT_DIR/lib/sd_card_ops.sh"

main() {
  parse_args "$@"
  require_root
  ensure_fs_tools
  validate_device
  unmount_partitions
  wipe_and_partition
  format_filesystem

  log "All done. You can now remove and reinsert the SD card or mount the new filesystem manually."
}

main "$@"

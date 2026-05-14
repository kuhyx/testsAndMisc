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

parse_args() {
  DEVICE=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --fs)
        if [[ $# -lt 2 ]]; then
          echo "Missing value for --fs" >&2
          exit 1
        fi
        FILESYSTEM="$2"
        shift 2
        ;;
      --dumbphone)
        # Force settings that are friendlier to older phones:
        # * MBR (dos) partition table
        # * Single ~30GiB FAT32 partition
        # * Leave remaining space unused
        DUMBPHONE_MODE=true
        FILESYSTEM="vfat"
        shift
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      /dev/*)
        DEVICE="$1"
        shift
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage
        exit 1
        ;;
    esac
  done

  export DEVICE FILESYSTEM DRY_RUN DUMBPHONE_MODE
}

detect_sd_card() {
  # List removable disks (RM=1, TYPE=disk)
  # Columns: NAME, RM, SIZE, MODEL, TRAN, TYPE
  local output
  output=$(lsblk -o NAME,RM,SIZE,MODEL,TRAN,TYPE -nr | awk '$2==1 && $6=="disk"') || true

  if [[ -z $output ]]; then
    echo "No removable disks detected. Please provide device explicitly (e.g., /dev/sda)." >&2
    exit 1
  fi

  mapfile -t candidates < <(echo "$output")

  if [[ ${#candidates[@]} -eq 1 ]]; then
    local name size model tran
    read -r name _ size model tran _ <<< "${candidates[0]}"
    DEVICE="/dev/${name}"
    log "Detected removable disk: $DEVICE (${size} ${model} ${tran})"
  else
    echo "Multiple removable disks detected:" >&2
    local i=1
    for line in "${candidates[@]}"; do
      local name size model tran
      read -r name _ size model tran _ <<< "$line"
      printf '  %d) /dev/%s  %s  %s %s\n' "$i" "$name" "$size" "$model" "$tran"
      ((i++))
    done

    while true; do
      read -r -p "Select device to format (1-${#candidates[@]}): " choice
      if [[ $choice =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#candidates[@]})); then
        local sel="${candidates[choice - 1]}"
        local name size model tran
        read -r name _ size model tran _ <<< "$sel"
        DEVICE="/dev/${name}"
        log "Selected device: $DEVICE (${size} ${model} ${tran})"
        break
      else
        echo "Invalid choice." >&2
      fi
    done
  fi
}

validate_device() {
  if [[ -z ${DEVICE:-} ]]; then
    detect_sd_card
  fi

  if [[ ! -b $DEVICE ]]; then
    echo "Device $DEVICE does not exist or is not a block device." >&2
    exit 1
  fi

  # Extra safety: refuse clearly system disks by checking if rootfs lives there
  local root_dev
  root_dev=$(findmnt -no SOURCE / || true)
  if [[ $root_dev == "$DEVICE"* ]]; then
    echo "Refusing to operate on $DEVICE because it appears to contain the root filesystem ($root_dev)." >&2
    exit 1
  fi
}

unmount_partitions() {
  local dev base part
  dev="$DEVICE"
  base="${dev##*/}"

  mapfile -t parts < <(lsblk -nr -o NAME,MOUNTPOINT "/dev/${base}" | awk 'NF==2 {print $1" "$2}') || true

  for entry in "${parts[@]:-}"; do
    read -r part mp <<< "$entry"
    if [[ -n $mp ]]; then
      run "umount \"$mp\""
    fi
  done
}

wipe_and_partition() {
  local dev="$DEVICE"

  if ! confirm "About to WIPE ALL DATA on $dev and create a new ${FILESYSTEM} filesystem. Continue?"; then
    echo "Aborted by user." >&2
    exit 1
  fi

  # Zap existing partition table
  run "wipefs -a \"$dev\""

  # Create a new partition table + partition layout
  # Using sfdisk for non-interactive, reproducible layout
  local sfdisk_input

  if [[ $DUMBPHONE_MODE == true ]]; then
    # Old phones often:
    #   * only support MBR (dos)
    #   * only support SD/SDHC (<=32GiB)
    # We create an MBR table and a single ~30GiB FAT32 partition, leaving the rest unused.
    # 30GiB ≈ 30 * 2^30 / 512 ≈ 62914560 sectors; start at 2048 for alignment.
    sfdisk_input=$'label: dos\n2048,62914560,c,*\n'
    if [[ $DRY_RUN == true ]]; then
      log "DRY RUN: echo -e '$sfdisk_input' | sfdisk $dev"
    else
      log "RUN: create MBR (dos) with ~30GiB FAT32 partition on $dev"
      echo -e "$sfdisk_input" | sfdisk "$dev"
    fi
  else
    # Default: GPT with one partition spanning the whole device
    sfdisk_input=$'label: gpt\n,;\n'
    if [[ $DRY_RUN == true ]]; then
      log "DRY RUN: echo -e '$sfdisk_input' | sfdisk $dev"
    else
      log "RUN: create GPT with one partition on $dev"
      echo -e "$sfdisk_input" | sfdisk "$dev"
    fi
  fi

  # Let the kernel re-read the partition table
  sleep 2
}

format_filesystem() {
  local dev base part
  dev="$DEVICE"
  base="${dev##*/}"
  part="/dev/${base}1"

  if [[ ! -b $part ]]; then
    echo "Expected partition $part not found after partitioning." >&2
    exit 1
  fi

  case "$FILESYSTEM" in
    exfat)
      run mkfs.exfat -n SDCARD "$part"
      ;;
    vfat | fat32)
      run mkfs.vfat -F32 -n SDCARD "$part"
      ;;
    ext4)
      run mkfs.ext4 -F -L SDCARD "$part"
      ;;
    *)
      echo "Unsupported filesystem type: $FILESYSTEM" >&2
      exit 1
      ;;
  esac

  log "Formatting completed on $part with filesystem $FILESYSTEM."
}

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

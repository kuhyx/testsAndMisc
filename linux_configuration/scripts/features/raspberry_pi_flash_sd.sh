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

discover_remote_laptop() {
  log_info "Auto-discovering remote laptop on local network..."

  ensure_dependencies

  local my_ip
  my_ip=$(ip -4 addr show | grep -oP '(?<=inet\s)(?!127\.)\d+(\.\d+){3}' | head -1)

  local gateway
  gateway=$(ip route | grep default | awk '{print $3}' | head -1)
  local network="${gateway%.*}.0/24"

  log_info "Local IP: $my_ip, Gateway: $gateway, Network: $network"
  log_info "Scanning network for SSH-enabled devices (using nmap)..."

  local ssh_hosts
  nmap -sn -T4 "$network" &> /dev/null || true
  ssh_hosts=$(nmap -p 22 --open -sT -T4 "$network" 2> /dev/null | grep "Nmap scan report" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -vw "$my_ip" | sort -u)

  if [[ -z $ssh_hosts ]]; then
    die "No SSH-enabled devices found on network"
  fi

  local host_count
  host_count=$(echo "$ssh_hosts" | wc -l)
  log_info "Found $host_count SSH-enabled device(s): $(echo "$ssh_hosts" | tr '\n' ' ')"

  local common_users=("$REMOTE_LAPTOP_USER" "kuchy" "kuhy" "$(whoami)" "pi" "user" "admin")
  local users=()
  for u in "${common_users[@]}"; do
    local is_dup=0
    for existing in "${users[@]}"; do
      if [[ $u == "$existing" ]]; then
        is_dup=1
        break
      fi
    done
    if [[ $is_dup -eq 0 ]]; then
      users+=("$u")
    fi
  done

  log_info "Will try usernames: ${users[*]}"

  local found_laptop=""
  local found_user=""
  local idx=0

  for ip in $ssh_hosts; do
    idx=$((idx + 1))

    if [[ $ip == "$gateway" ]]; then
      log_info "[$idx/$host_count] Skipping $ip (gateway)"
      continue
    fi

    log_info "[$idx/$host_count] $ip - Trying SSH key access with common usernames..."

    for try_user in "${users[@]}"; do
      if ssh -o BatchMode=yes -o ConnectTimeout=2 -o StrictHostKeyChecking=accept-new "${try_user}@${ip}" "echo ok" 2> /dev/null | grep -q "ok"; then
        log_success "[$idx/$host_count] $ip - SSH key access confirmed with user '$try_user'!"
        found_user="$try_user"

        log_info "[$idx/$host_count] $ip - Checking for SD card..."
        local has_sd
        has_sd=$(ssh -o BatchMode=yes -o ConnectTimeout=2 "${try_user}@${ip}" "lsblk -d -o NAME,RM,TRAN 2>/dev/null | grep -E '1.*(usb|mmc)' | head -1" 2> /dev/null || true)

        if [[ -n $has_sd ]]; then
          log_success "[$idx/$host_count] $ip - Found SD card: $has_sd"
          found_laptop="$ip"
          break 2
        else
          log_warning "[$idx/$host_count] $ip - No SD card detected, saving as fallback..."
          if [[ -z $found_laptop ]]; then
            found_laptop="$ip"
          fi
        fi
        break
      fi
    done
  done

  if [[ -z $found_laptop ]] || [[ -z $found_user ]]; then
    log_warning "No device with passwordless SSH found using common usernames."

    found_laptop=$(echo "$ssh_hosts" | grep -vw "$gateway" | head -1)

    if [[ -z $found_laptop ]]; then
      die "Could not find any suitable SSH-enabled device"
    fi

    log_info "Found SSH host at $found_laptop but need credentials."
    read -r -p "Enter username for $found_laptop: " found_user

    if [[ -z $found_user ]]; then
      die "No username provided"
    fi
  fi

  REMOTE_LAPTOP_IP="$found_laptop"
  REMOTE_LAPTOP_USER="$found_user"
  log_success "Selected remote laptop: ${REMOTE_LAPTOP_USER}@${REMOTE_LAPTOP_IP}"

  save_config
}

setup_ssh_key_to_remote() {
  local remote_host="$1"
  local remote_user="$2"

  if ssh -o BatchMode=yes -o ConnectTimeout=5 "${remote_user}@${remote_host}" "echo 'SSH key works'" 2> /dev/null; then
    log_success "SSH key authentication to ${remote_user}@${remote_host} already configured"
    return 0
  fi

  log_info "Setting up SSH key authentication to ${remote_user}@${remote_host}..."

  if [[ ! -f ~/.ssh/id_rsa.pub ]] && [[ ! -f ~/.ssh/id_ed25519.pub ]]; then
    log_info "Generating SSH key..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -q
  fi

  log_info "Copying SSH key to remote host (you may be prompted for password)..."

  if command -v ssh-copy-id &> /dev/null; then
    ssh-copy-id -o StrictHostKeyChecking=no "${remote_user}@${remote_host}"
  else
    local pub_key
    pub_key=$(cat ~/.ssh/id_ed25519.pub 2> /dev/null || cat ~/.ssh/id_rsa.pub)
    ssh -o StrictHostKeyChecking=no "${remote_user}@${remote_host}" "mkdir -p ~/.ssh && echo '$pub_key' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
  fi

  log_success "SSH key authentication configured"
}

# =============================================================================
# Download and Flash Functions
# =============================================================================

download_raspberry_pi_os() {
  local download_dir="/tmp/rpi-image"
  local image_url="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2024-11-19/2024-11-19-raspios-bookworm-arm64-lite.img.xz"
  local image_file="$download_dir/raspios.img.xz"
  local extracted_image="$download_dir/raspios.img"
  local expected_size=459000608

  mkdir -p "$download_dir"

  if [[ -f $extracted_image ]]; then
    log_info "Using existing image at $extracted_image"
    echo "$extracted_image"
    return
  fi

  if [[ -f $image_file ]]; then
    local actual_size
    actual_size=$(stat -c%s "$image_file" 2> /dev/null || stat -f%z "$image_file" 2> /dev/null || echo 0)
    if [[ $actual_size -lt $expected_size ]]; then
      log_warning "Incomplete download detected ($actual_size < $expected_size bytes), re-downloading..."
      rm -f "$image_file"
    else
      log_info "Image archive already downloaded"
    fi
  fi

  if [[ ! -f $image_file ]]; then
    log_info "Downloading Raspberry Pi OS Lite (64-bit)..."
    log_info "This may take a while depending on your internet connection..."

    if command -v aria2c &> /dev/null; then
      aria2c -x 4 -c -d "$download_dir" --out="raspios.img.xz" "$image_url" >&2
    elif command -v wget &> /dev/null; then
      wget --continue --show-progress -O "$image_file" "$image_url" >&2
    elif command -v curl &> /dev/null; then
      curl -L -C - -o "$image_file" "$image_url" --progress-bar >&2
    else
      die "No download tool available. Install wget, curl, or aria2c"
    fi

    local actual_size
    actual_size=$(stat -c%s "$image_file" 2> /dev/null || stat -f%z "$image_file" 2> /dev/null || echo 0)
    if [[ $actual_size -lt $expected_size ]]; then
      die "Download incomplete: got $actual_size bytes, expected $expected_size"
    fi
    log_success "Download complete: $actual_size bytes"
  fi

  log_info "Extracting image..."
  xz -dk "$image_file"

  if [[ ! -f $extracted_image ]]; then
    die "Failed to extract image"
  fi

  echo "$extracted_image"
}

# =============================================================================
# Local Flash
# =============================================================================

phase_flash_local() {
  check_root

  log_info "=== Flash Raspberry Pi OS to SD Card (Local) ==="

  # Detect SD card
  log_info "Detecting removable storage devices..."
  local devices
  devices=$(lsblk -d -o NAME,SIZE,TYPE,RM,TRAN | grep -E "disk.*1.*usb|disk.*1.*mmc" | awk '{print "/dev/"$1" ("$2")"}')

  if [[ -z $devices ]]; then
    log_warning "No removable devices detected automatically."
    lsblk -d -o NAME,SIZE,TYPE,RM,TRAN
    read -r -p "Enter the SD card device path (e.g., /dev/sdb): " SD_CARD_DEVICE
  else
    echo "Detected removable devices:"
    echo "$devices"
    read -r -p "Enter the SD card device path from above (e.g., /dev/sdb): " SD_CARD_DEVICE
  fi

  if [[ ! -b $SD_CARD_DEVICE ]]; then
    die "Device $SD_CARD_DEVICE does not exist or is not a block device"
  fi

  local root_device
  root_device=$(findmnt -n -o SOURCE / | sed 's/[0-9]*$//' | sed 's/p[0-9]*$//')
  if [[ $SD_CARD_DEVICE == "$root_device" ]]; then
    die "Cannot flash to the system drive!"
  fi

  auto_generate_pi_password

  local encrypted_password
  encrypted_password=$(echo "$PI_PASSWORD" | openssl passwd -6 -stdin)

  save_config

  local image_path
  image_path=$(download_raspberry_pi_os)

  log_warning "This will ERASE ALL DATA on $SD_CARD_DEVICE"
  read -r -p "Are you sure you want to continue? (yes/no): " confirm

  if [[ $confirm != "yes" ]]; then
    die "Aborted by user"
  fi

  log_info "Unmounting partitions on $SD_CARD_DEVICE..."
  for partition in "${SD_CARD_DEVICE}"*; do
    if mountpoint -q "$partition" 2> /dev/null || mount | grep -q "$partition"; then
      umount "$partition" 2> /dev/null || true
    fi
  done

  log_info "Flashing image to SD card..."
  dd if="$image_path" of="$SD_CARD_DEVICE" bs=4M status=progress conv=fsync
  sync
  log_success "Image flashed successfully!"

  # Configure headless boot
  log_info "Configuring headless boot..."
  sleep 2
  partprobe "$SD_CARD_DEVICE" 2> /dev/null || true
  sleep 2

  local boot_partition
  if [[ -b "${SD_CARD_DEVICE}1" ]]; then
    boot_partition="${SD_CARD_DEVICE}1"
  elif [[ -b "${SD_CARD_DEVICE}p1" ]]; then
    boot_partition="${SD_CARD_DEVICE}p1"
  else
    die "Could not find boot partition"
  fi

  local boot_mount="/tmp/rpi-boot"
  mkdir -p "$boot_mount"
  mount "$boot_partition" "$boot_mount"

  touch "$boot_mount/ssh"
  log_success "SSH enabled"

  echo "${PI_USER}:${encrypted_password}" > "$boot_mount/userconf.txt"
  log_success "User '$PI_USER' configured"

  local root_partition
  if [[ -b "${SD_CARD_DEVICE}2" ]]; then
    root_partition="${SD_CARD_DEVICE}2"
  elif [[ -b "${SD_CARD_DEVICE}p2" ]]; then
    root_partition="${SD_CARD_DEVICE}p2"
  fi

  if [[ -n $root_partition ]]; then
    local root_mount="/tmp/rpi-root"
    mkdir -p "$root_mount"
    mount "$root_partition" "$root_mount"

    echo "$PI_HOSTNAME" > "$root_mount/etc/hostname"
    sed -i "s/raspberrypi/$PI_HOSTNAME/g" "$root_mount/etc/hosts"

    log_success "Hostname set to '$PI_HOSTNAME'"

    umount "$root_mount"
  fi

  umount "$boot_mount"
  sync

  log_success "SD card configured for headless boot!"
  log_success "Flash complete!"
  echo
  log_info "Pi credentials:"
  log_info "  User: $PI_USER"
  log_info "  Password: $PI_PASSWORD"
  log_info "  Hostname: $PI_HOSTNAME"
  echo
  log_info "Next steps:"
  log_info "1. Remove SD card and insert into Raspberry Pi"
  log_info "2. Connect the Pi to power and network"
  log_info "3. Wait 2-3 minutes for first boot"
}

# =============================================================================
# Remote Flash
# =============================================================================

phase_flash_remote() {
  log_info "=== Flash Raspberry Pi OS to SD Card on Remote Laptop ==="

  discover_remote_laptop

  setup_ssh_key_to_remote "$REMOTE_LAPTOP_IP" "$REMOTE_LAPTOP_USER"

  local remote="${REMOTE_LAPTOP_USER}@${REMOTE_LAPTOP_IP}"

  log_info "Checking for SD card on remote laptop..."
  echo "Block devices on ${remote}:"
  ssh "$remote" "lsblk -d -o NAME,SIZE,TYPE,RM,TRAN,MODEL" || true
  echo

  log_info "Auto-detecting SD card on remote laptop..."
  local sd_device
  sd_device=$(ssh "$remote" "lsblk -d -o NAME,RM,TRAN | grep -E '1.*(usb|mmc)' | awk '{print \"/dev/\"\$1}' | head -1" 2> /dev/null || true)

  if [[ -z $sd_device ]]; then
    die "No SD card detected on remote laptop. Please insert an SD card and try again."
  fi

  local sd_info
  # shellcheck disable=SC2029  # Intentional client-side expansion
  sd_info=$(ssh "$remote" "lsblk -d -o NAME,SIZE,MODEL $sd_device 2>/dev/null | tail -1" || true)

  log_success "Auto-detected SD card: $sd_device ($sd_info)"
  SD_CARD_DEVICE="$sd_device"

  # shellcheck disable=SC2029  # Intentional client-side expansion
  if ! ssh "$remote" "[[ -b '$SD_CARD_DEVICE' ]]" 2> /dev/null; then
    die "Device $SD_CARD_DEVICE does not exist on remote laptop"
  fi

  auto_generate_pi_password
  log_success "Pi user '$PI_USER' password: $PI_PASSWORD"

  local encrypted_password
  encrypted_password=$(echo "$PI_PASSWORD" | openssl passwd -6 -stdin)

  save_config

  log_info "Copying script to remote laptop..."
  scp "$0" "${remote}:/tmp/raspberry_pi_flash_sd.sh"

  log_info "Executing flash on remote laptop..."
  log_warning "This will ERASE ALL DATA on ${SD_CARD_DEVICE} on the remote laptop!"
  log_info "Proceeding automatically in 5 seconds... (Ctrl+C to cancel)"
  sleep 5

  ssh -tt "$remote" "sudo SD_CARD_DEVICE='$SD_CARD_DEVICE' PI_USER='$PI_USER' PI_HOSTNAME='$PI_HOSTNAME' bash /tmp/raspberry_pi_flash_sd.sh execute-remote '$encrypted_password'"

  log_success "Flash complete!"
  echo
  log_info "Pi credentials:"
  log_info "  User: $PI_USER"
  log_info "  Password: $PI_PASSWORD"
  log_info "  Hostname: $PI_HOSTNAME"
  echo
  log_info "Next steps:"
  log_info "1. Remove SD card from the laptop and insert into Raspberry Pi"
  log_info "2. Connect the Pi to power and network"
  log_info "3. Wait 2-3 minutes for first boot"
}

# Called on the remote laptop by phase_flash_remote
phase_execute_remote() {
  check_root

  local encrypted_password="${1:-}"

  log_info "=== Executing Flash on Remote Laptop ==="

  if [[ -z $SD_CARD_DEVICE ]]; then
    die "SD_CARD_DEVICE not set"
  fi

  local image_path
  image_path=$(download_raspberry_pi_os)

  log_info "Unmounting partitions on $SD_CARD_DEVICE..."
  for partition in "${SD_CARD_DEVICE}"*; do
    if mountpoint -q "$partition" 2> /dev/null || mount | grep -q "$partition"; then
      umount "$partition" 2> /dev/null || true
    fi
  done

  log_info "Flashing image to SD card..."
  dd if="$image_path" of="$SD_CARD_DEVICE" bs=4M status=progress conv=fsync
  sync
  log_success "Image flashed successfully!"

  log_info "Configuring headless boot..."
  sleep 2
  partprobe "$SD_CARD_DEVICE" 2> /dev/null || true
  sleep 2

  local boot_partition
  if [[ -b "${SD_CARD_DEVICE}1" ]]; then
    boot_partition="${SD_CARD_DEVICE}1"
  elif [[ -b "${SD_CARD_DEVICE}p1" ]]; then
    boot_partition="${SD_CARD_DEVICE}p1"
  else
    die "Could not find boot partition"
  fi

  local boot_mount="/tmp/rpi-boot"
  mkdir -p "$boot_mount"
  mount "$boot_partition" "$boot_mount"

  touch "$boot_mount/ssh"
  log_success "SSH enabled"

  if [[ -n $encrypted_password ]]; then
    echo "${PI_USER}:${encrypted_password}" > "$boot_mount/userconf.txt"
    log_success "User '$PI_USER' configured"
  fi

  local root_partition
  if [[ -b "${SD_CARD_DEVICE}2" ]]; then
    root_partition="${SD_CARD_DEVICE}2"
  elif [[ -b "${SD_CARD_DEVICE}p2" ]]; then
    root_partition="${SD_CARD_DEVICE}p2"
  fi

  if [[ -n $root_partition ]]; then
    local root_mount="/tmp/rpi-root"
    mkdir -p "$root_mount"
    mount "$root_partition" "$root_mount"

    echo "$PI_HOSTNAME" > "$root_mount/etc/hostname"
    sed -i "s/raspberrypi/$PI_HOSTNAME/g" "$root_mount/etc/hosts"

    log_success "Hostname set to '$PI_HOSTNAME'"

    umount "$root_mount"
  fi

  umount "$boot_mount"
  sync

  log_success "SD card configured for headless boot!"
}

# =============================================================================
# Main
# =============================================================================

show_help() {
  cat << 'EOF'
Raspberry Pi SD Card Flash Script

Usage: ./raspberry_pi_flash_sd.sh <command>

Commands:
  local              Flash SD card locally (requires root)
  remote             Flash SD card on a remote laptop via SSH
  execute-remote     Internal: executed on remote laptop
  help               Show this help message

The script will:
1. Auto-discover a remote laptop with an SD card (for remote mode)
2. Download Raspberry Pi OS Lite (64-bit)
3. Flash the image to the SD card
4. Configure headless boot (SSH enabled, user created, hostname set)

Credentials are auto-generated and saved to .raspberry_pi.conf

Examples:
  # Flash locally (run as root)
  sudo ./raspberry_pi_flash_sd.sh local

  # Flash on remote laptop
  ./raspberry_pi_flash_sd.sh remote
EOF
}

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

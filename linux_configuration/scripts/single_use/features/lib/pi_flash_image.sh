#!/bin/bash
# OS image download and the local flash phase.
#
# Sourced by raspberry_pi_flash_sd.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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

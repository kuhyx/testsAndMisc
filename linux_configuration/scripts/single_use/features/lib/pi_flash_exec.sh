#!/bin/bash
# Flashing from the remote laptop.
#
# Sourced by raspberry_pi_flash_sd.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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

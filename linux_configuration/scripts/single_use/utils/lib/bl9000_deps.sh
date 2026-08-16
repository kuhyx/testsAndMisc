#!/bin/bash
# Dependency installation and prerequisite checks.
#
# Sourced by root_bl9000.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

install_dependencies() {
  print_header "Installing Dependencies"

  local packages=()
  local missing=()

  # Check for required commands
  if ! command -v adb > /dev/null 2>&1; then
    packages+=("android-tools")
    missing+=("adb")
  fi

  if ! command -v fastboot > /dev/null 2>&1 && ! pacman -Q android-tools > /dev/null 2>&1; then
    packages+=("android-tools")
    missing+=("fastboot")
  fi

  if ! command -v unzip > /dev/null 2>&1; then
    packages+=("unzip")
    missing+=("unzip")
  fi

  if ! command -v curl > /dev/null 2>&1; then
    packages+=("curl")
    missing+=("curl")
  fi

  if ! command -v python3 > /dev/null 2>&1; then
    packages+=("python")
    missing+=("python3")
  fi

  if ! command -v git > /dev/null 2>&1; then
    packages+=("git")
    missing+=("git")
  fi

  # Check for libusb and fuse2 (needed for mtkclient)
  if ! pacman -Q libusb > /dev/null 2>&1; then
    packages+=("libusb")
    missing+=("libusb")
  fi

  if ! pacman -Q fuse2 > /dev/null 2>&1; then
    packages+=("fuse2")
    missing+=("fuse2")
  fi

  # Check for python-protobuf (needed for boot image tools)
  if ! python3 -c "import google.protobuf" 2> /dev/null; then
    packages+=("python-protobuf")
    missing+=("python-protobuf")
  fi

  if [[ ${#missing[@]} -eq 0 ]]; then
    log "All dependencies are already installed."
    return 0
  fi

  log "Missing dependencies: ${missing[*]}"

  # Remove duplicates
  readarray -t packages < <(printf '%s\n' "${packages[@]}" | sort -u)

  if ! confirm "Install missing packages: ${packages[*]}?"; then
    die "Cannot proceed without required dependencies."
  fi

  log "Installing packages: ${packages[*]}"
  sudo pacman -S --needed --noconfirm "${packages[@]}" || die "Failed to install dependencies"

  log "Dependencies installed successfully."
}

setup_udev_rules() {
  print_header "Setting Up USB Access"

  local udev_file="/etc/udev/rules.d/51-android.rules"
  local mtk_udev_dir="${WORK_DIR}/mtkclient/mtkclient/Setup/Linux"

  # Install MTKClient udev rules if mtkclient is present
  if [[ -d "${WORK_DIR}/mtkclient" ]]; then
    log "Installing MTKClient udev rules..."
    if [[ -d $mtk_udev_dir ]]; then
      sudo cp "$mtk_udev_dir"/*.rules /etc/udev/rules.d/ 2> /dev/null || warn "Failed to copy MTKClient rules"
    fi
  fi

  if [[ -f $udev_file ]]; then
    log "Android udev rules already exist at $udev_file"
  else
    if ! confirm "Create udev rules for Android device access?"; then
      warn "Skipping udev rules. You may need to run commands with sudo."
      return 0
    fi

    log "Creating Android udev rules..."

    # Create comprehensive udev rules for Android devices
    sudo tee "$udev_file" > /dev/null << 'EOF'
# Android Debug Bridge (ADB) devices
# Add your device's vendor ID if not listed

# Google
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666", GROUP="adbusers"
# MediaTek (common in BL9000)
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="adbusers"
# Generic catch-all for Android devices
SUBSYSTEM=="usb", ATTR{idVendor}=="*", ATTR{idProduct}=="*", MODE="0666", GROUP="adbusers", SYMLINK+="android%n"
EOF
  fi

  # Create adbusers group if it doesn't exist
  if ! getent group adbusers > /dev/null; then
    sudo groupadd -r adbusers
    log "Created adbusers group"
  fi

  # Add current user to adbusers and plugdev groups
  if ! groups "$USER" | grep -q '\badbusers\b'; then
    sudo usermod -aG adbusers "$USER"
    log "Added $USER to adbusers group"
  fi

  if ! getent group plugdev > /dev/null; then
    sudo groupadd -r plugdev
  fi

  if ! groups "$USER" | grep -q '\bplugdev\b'; then
    sudo usermod -aG plugdev "$USER"
    log "Added $USER to plugdev group"
  fi

  if ! getent group dialout > /dev/null; then
    sudo groupadd -r dialout
  fi

  if ! groups "$USER" | grep -q '\bdialout\b'; then
    sudo usermod -aG dialout "$USER"
    log "Added $USER to dialout group"
    warn "You need to log out and back in for group membership to take effect."
    warn "Alternatively, run: newgrp dialout"
  fi

  # Reload udev rules
  sudo udevadm control --reload-rules
  sudo udevadm trigger

  log "USB access configured successfully."
}

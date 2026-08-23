#!/bin/bash
# Usage text and the argument parsing help.
#
# Sourced by root_bl9000.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

usage() {
  cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] [COMMAND]

Root BL9000 phone from Arch Linux using Magisk.

Commands:
  install-deps      Install required dependencies (adb, fastboot, tools)
  install-mtk       Install MTKClient for MediaTek boot extraction
  check             Check device connection and prerequisites
  backup            Backup phone data before unlocking bootloader
  unlock            Unlock bootloader (WARNING: wipes all data!)
  extract-mtk       Extract boot.img using MTKClient (for MediaTek devices)
  patch             Patch boot.img with Magisk (manual step on phone)
  flash [IMG]       Flash patched boot image (uses magisk_patched.img or specified file)
  auto-root         Automated: extract -> patch -> flash in one command
  root              Extract boot, patch with Magisk, and flash
  full              Run complete rooting process (deps + unlock + root)
  clean             Remove temporary working directory
  help              Show this message

Options:
  -h, --help        Show this message
  --work-dir DIR    Set working directory (default: $WORK_DIR)
  --boot-img FILE   Use existing boot.img instead of extracting from device

Examples:
  $SCRIPT_NAME install-deps        # Install required tools
  $SCRIPT_NAME install-mtk         # Install MTKClient for boot extraction
  $SCRIPT_NAME check               # Verify device connection
  $SCRIPT_NAME backup              # Backup phone data first!
  $SCRIPT_NAME extract-mtk         # Extract boot.img with MTKClient
  $SCRIPT_NAME auto-root           # Automated rooting (extract + patch + flash)
  $SCRIPT_NAME full                # Complete rooting process
  $SCRIPT_NAME root                # Root only (assumes bootloader unlocked)

WARNING: Unlocking the bootloader will ERASE ALL DATA on your phone!
         Make sure to back up important data before proceeding.

EOF
}



run_full_process() {
  print_header "BL9000 Full Root Process"

  log "Starting complete rooting process..."

  install_dependencies || die "Failed to install dependencies"
  setup_udev_rules || true

  echo
  if ! confirm "Continue to device check?"; then
    die "Process cancelled by user"
  fi

  check_device || die "Device check failed"

  echo
  if ! confirm "Continue to backup device data?"; then
    die "Process cancelled by user"
  fi

  backup_device_data || warn "Backup failed or incomplete"

  echo
  if ! confirm "Continue to bootloader unlock?"; then
    die "Process cancelled by user"
  fi

  unlock_bootloader || die "Bootloader unlock failed"

  echo
  log "Please complete device setup and re-enable USB debugging, then press Enter..."
  read -r

  check_device || die "Device check failed after unlock"

  download_magisk || die "Failed to download Magisk"
  extract_boot_image || die "Failed to extract boot image"
  patch_boot_with_magisk || die "Failed to patch boot image"
  flash_patched_boot || die "Failed to flash patched boot"

  log "Full root process completed successfully!"
}

run_root_only() {
  print_header "BL9000 Root Process (Skip Unlock)"

  log "Starting root process (assuming bootloader is already unlocked)..."

  check_device || die "Device check failed"
  download_magisk || die "Failed to download Magisk"
  extract_boot_image || die "Failed to extract boot image"
  patch_boot_with_magisk || die "Failed to patch boot image"
  flash_patched_boot || die "Failed to flash patched boot"

  log "Root process completed successfully!"
}

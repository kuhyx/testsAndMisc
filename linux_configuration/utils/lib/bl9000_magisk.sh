#!/bin/bash
# Boot image patching with Magisk.
#
# Sourced by root_bl9000.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

patch_boot_with_magisk() {
  print_header "Patching Boot Image with Magisk"

  if [[ ! -f ${BOOT_IMG:-} ]]; then
    die "Boot image not found: ${BOOT_IMG:-none}"
  fi

  local magisk_apk="$WORK_DIR/magisk.apk"
  if [[ ! -f $magisk_apk ]]; then
    die "Magisk APK not found. Run download step first."
  fi

  log "Checking if device is connected..."
  if ! adb devices | grep -q "device$"; then
    die "No device detected. Make sure USB debugging is enabled and device is connected."
  fi

  log "Installing Magisk APK on device..."
  if ! adb install -r "$magisk_apk" 2> /dev/null; then
    warn "Magisk APK installation failed (may already be installed)"
  fi

  log "Pushing boot image to device..."
  adb push "$BOOT_IMG" /sdcard/Download/boot.img || die "Failed to push boot image"

  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  MANUAL STEP REQUIRED"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo
  echo "On your phone:"
  echo "1. Open the Magisk app"
  echo "2. Tap 'Install' next to Magisk"
  echo "3. Select 'Select and Patch a File'"
  echo "4. Navigate to Downloads and select boot.img"
  echo "5. Tap 'Let's Go' and wait for patching to complete"
  echo "6. The patched file will be saved as magisk_patched_*.img"
  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo

  if ! confirm "Have you completed patching the boot image in Magisk app?"; then
    error "Patching cancelled by user"
    return 1
  fi

  log "Pulling patched boot image from device..."

  local patched_img
  patched_img=$(adb shell "ls /sdcard/Download/magisk_patched_*.img 2>/dev/null" | tr -d '\r\n' | head -n1 || echo "")

  if [[ -z $patched_img ]]; then
    error "Could not find patched boot image on device."
    echo "Please ensure the patching completed successfully in Magisk app."
    return 1
  fi

  PATCHED_BOOT_IMG="$WORK_DIR/magisk_patched.img"
  if ! adb pull "$patched_img" "$PATCHED_BOOT_IMG"; then
    error "Failed to pull patched boot image"
    return 1
  fi

  log "Patched boot image saved to: $PATCHED_BOOT_IMG"
  return 0
}

flash_patched_boot() {
  print_header "Flashing Patched Boot Image"

  if [[ ! -f ${PATCHED_BOOT_IMG:-} ]]; then
    die "Patched boot image not found: ${PATCHED_BOOT_IMG:-none}"
  fi

  echo
  echo -e "${YELLOW}This will flash the patched boot image to your device.${NC}"
  echo "Device uses A/B partitions - will flash to boot_a"
  echo

  if ! confirm "Proceed with flashing?"; then
    log "Flashing cancelled by user"
    return 1
  fi

  log "Rebooting to bootloader..."
  adb reboot bootloader || die "Failed to reboot to bootloader"

  log "Waiting for fastboot mode..."
  sleep 5

  if ! sudo fastboot devices | grep -q .; then
    die "Device not detected in fastboot mode"
  fi

  log "Flashing patched boot image to boot_a..."
  if ! sudo fastboot flash boot_a "$PATCHED_BOOT_IMG"; then
    error "Failed to flash boot image"
    return 1
  fi

  log "Flashed successfully!"
  log "Rebooting device..."
  sudo fastboot reboot

  log "Waiting for device to boot..."
  sleep 10
  adb wait-for-device || true

  echo
  echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║              Root Process Complete!                   ║${NC}"
  echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
  echo
  echo "Your BL9000 phone should now be rooted with Magisk!"
  echo
  echo "Next steps:"
  echo "1. Open the Magisk app on your phone"
  echo "2. Verify that it shows 'Installed' for both Magisk and App"
  echo "3. Grant root access to apps as needed"
  echo "4. Install Magisk modules if desired"
  echo
  echo "Note: Some banking and secure apps may not work with root."
  echo "      Use Magisk's DenyList feature to hide root from specific apps."
  echo

  return 0
}

clean_work_dir() {
  if [[ -d $WORK_DIR ]]; then
    log "Removing working directory: $WORK_DIR"
    rm -rf "$WORK_DIR"
    log "Cleaned successfully"
  else
    log "Work directory doesn't exist: $WORK_DIR"
  fi
}

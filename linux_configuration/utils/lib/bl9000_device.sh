#!/bin/bash
# Device detection and connection checks.
#
# Sourced by root_bl9000.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

check_device() {
  print_header "Checking Device Connection"

  log "Starting ADB server..."
  adb start-server > /dev/null 2>&1 || true

  log "Waiting for device..."
  if ! adb wait-for-device; then
    error "Failed to detect device via ADB."
    echo
    echo "Troubleshooting steps:"
    echo "1. Make sure USB debugging is enabled on your phone"
    echo "   Settings → About Phone → Tap Build Number 7 times"
    echo "   Settings → Developer Options → Enable USB Debugging"
    echo "2. Connect your phone via USB cable"
    echo "3. Accept the 'Allow USB debugging' prompt on your phone"
    echo "4. Run: adb devices"
    echo
    return 1
  fi

  local device_info
  device_info=$(adb devices -l | grep -v "List of devices" | grep -v "^$" | head -n1)

  if [[ -z $device_info ]]; then
    error "No device detected"
    return 1
  fi

  log "Device connected: $device_info"

  # Check device properties
  local model
  model=$(adb shell getprop ro.product.model 2> /dev/null | tr -d '\r\n' || echo "Unknown")
  log "Model: $model"

  local android_version
  android_version=$(adb shell getprop ro.build.version.release 2> /dev/null | tr -d '\r\n' || echo "Unknown")
  log "Android version: $android_version"

  local battery_level
  battery_level=$(adb shell dumpsys battery | grep level | awk '{print $2}' | tr -d '\r\n' || echo "Unknown")
  log "Battery level: ${battery_level}%"

  if [[ $battery_level != "Unknown" && $battery_level -lt 50 ]]; then
    warn "Battery level is below 50%. Charge your phone before proceeding."
    if ! confirm "Continue anyway?"; then
      return 1
    fi
  fi

  # Check if bootloader is unlocked
  local unlock_status
  unlock_status=$(adb shell getprop ro.boot.verifiedbootstate 2> /dev/null | tr -d '\r\n' || echo "unknown")
  if [[ $unlock_status == "orange" || $unlock_status == "red" ]]; then
    log "Bootloader unlock status: ${GREEN}UNLOCKED${NC}"
  else
    warn "Bootloader appears to be LOCKED. You'll need to unlock it to root."
  fi

  # Check if OEM unlocking is enabled
  local oem_unlock
  oem_unlock=$(adb shell getprop sys.oem_unlock_allowed 2> /dev/null | tr -d '\r\n' || echo "unknown")
  if [[ $oem_unlock == "1" ]]; then
    log "OEM unlocking: ${GREEN}ENABLED${NC}"
  else
    warn "OEM unlocking is not enabled in Developer Options."
    echo "Enable it at: Settings → Developer Options → OEM unlocking"
  fi

  return 0
}

unlock_bootloader() {
  print_header "Unlocking Bootloader"

  echo
  echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${RED}║                         WARNING                               ║${NC}"
  echo -e "${RED}║                                                               ║${NC}"
  echo -e "${RED}║  Unlocking the bootloader will ERASE ALL DATA on your phone! ║${NC}"
  echo -e "${RED}║                                                               ║${NC}"
  echo -e "${RED}║  This includes:                                               ║${NC}"
  echo -e "${RED}║  - All apps and app data                                      ║${NC}"
  echo -e "${RED}║  - Photos, videos, and files                                  ║${NC}"
  echo -e "${RED}║  - System settings                                            ║${NC}"
  echo -e "${RED}║  - Everything else on internal storage                        ║${NC}"
  echo -e "${RED}║                                                               ║${NC}"
  echo -e "${RED}║  Make sure you have backed up important data!                 ║${NC}"
  echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
  echo

  if ! confirm "Have you backed up all important data and want to proceed?"; then
    log "Bootloader unlock cancelled by user."
    return 1
  fi

  if ! confirm "Are you ABSOLUTELY SURE? This cannot be undone!"; then
    log "Bootloader unlock cancelled by user."
    return 1
  fi

  log "Rebooting device to bootloader..."
  adb reboot bootloader || die "Failed to reboot to bootloader"

  log "Waiting for fastboot mode..."
  sleep 5

  if ! fastboot devices | grep -q .; then
    error "Device not detected in fastboot mode."
    echo
    echo "If the device doesn't enter fastboot automatically:"
    echo "1. Power off the phone completely"
    echo "2. Hold Volume Down + Power buttons simultaneously"
    echo "3. Release when you see the bootloader/fastboot screen"
    echo "4. Run: fastboot devices"
    echo
    return 1
  fi

  log "Device in fastboot mode"

  # Check current bootloader status
  local bl_status
  bl_status=$(fastboot getvar unlocked 2>&1 | grep "unlocked:" | awk '{print $2}' || echo "unknown")
  if [[ $bl_status == "yes" ]]; then
    log "Bootloader is already unlocked."
    fastboot reboot
    return 0
  fi

  log "Attempting to unlock bootloader..."

  # Try different unlock commands (varies by device)
  if fastboot flashing unlock 2>&1 | grep -qi "okay\|finished"; then
    log "Bootloader unlock command sent successfully."
  elif fastboot oem unlock 2>&1 | grep -qi "okay\|finished"; then
    log "Bootloader unlock command sent successfully."
  else
    error "Bootloader unlock command may have failed."
    echo
    echo "On your phone:"
    echo "1. Use volume buttons to select 'Unlock the bootloader'"
    echo "2. Press power button to confirm"
    echo

    if ! confirm "Did you complete the unlock on the device?"; then
      fastboot reboot
      return 1
    fi
  fi

  log "Rebooting device..."
  fastboot reboot || true

  log "Bootloader unlocked successfully!"
  log "Device will now boot up and perform factory reset..."
  log "Waiting for device to come back online..."

  sleep 10
  adb wait-for-device || true

  log "Please complete the initial setup on your phone, then re-enable USB debugging."
  echo

  return 0
}

download_magisk() {
  print_header "Downloading Magisk"

  local magisk_apk="$WORK_DIR/magisk.apk"

  if [[ -f $magisk_apk ]]; then
    log "Magisk APK already downloaded at $magisk_apk"
    return 0
  fi

  log "Downloading latest Magisk APK..."
  if ! curl -L -o "$magisk_apk" "$MAGISK_APK_URL"; then
    error "Failed to download Magisk APK"
    return 1
  fi

  log "Magisk downloaded successfully: $magisk_apk"
  return 0
}

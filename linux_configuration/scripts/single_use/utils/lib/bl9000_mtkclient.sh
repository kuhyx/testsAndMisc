#!/bin/bash
# mtkclient checkout and setup.
#
# Sourced by root_bl9000.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

install_mtkclient() {
  print_header "Installing MTKClient"

  local mtk_dir="${WORK_DIR}/mtkclient"

  if [[ -d $mtk_dir && -f "$mtk_dir/mtk.py" ]]; then
    log "MTKClient already installed at $mtk_dir"
    return 0
  fi

  if ! confirm "Install MTKClient for MediaTek boot image extraction?"; then
    return 1
  fi

  log "Cloning MTKClient repository..."
  if ! git clone https://github.com/bkerler/mtkclient "$mtk_dir"; then
    error "Failed to clone MTKClient"
    return 1
  fi

  log "Installing MTKClient Python dependencies..."
  # Subshell so the cd cannot leak, and so a failure cannot strand the caller
  # in $mtk_dir the way the old `cd -` did on an early return.
  (
    cd "$mtk_dir" || exit 1
    python3 -m pip install --user -r requirements.txt || warn "Some dependencies may have failed to install"
    python3 -m pip install --user . || warn "MTKClient installation may be incomplete"
  ) || warn "MTKClient installation may be incomplete"

  log "MTKClient installed successfully"
  return 0
}

extract_boot_with_mtkclient() {
  print_header "Extracting Boot with MTKClient"

  local mtk_dir="${WORK_DIR}/mtkclient"
  local boot_img="$WORK_DIR/boot.img"
  local boot_a_img="$WORK_DIR/boot_a.img"
  local vbmeta_a_img="$WORK_DIR/vbmeta_a.img"

  if [[ ! -d $mtk_dir ]]; then
    error "MTKClient not installed. Run: $SCRIPT_NAME install-mtk"
    return 1
  fi

  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  MTKClient Boot ROM Mode Instructions"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo
  echo "BEFORE continuing, you MUST:"
  echo
  echo "  1. Power off your phone COMPLETELY"
  echo "  2. DISCONNECT the USB cable from your phone"
  echo "  3. Have the USB cable ready in your hand"
  echo
  echo "When you press Enter:"
  echo
  echo "  4. Press and hold BOTH Volume buttons (Up + Down)"
  echo "  5. While holding BOTH buttons, connect USB cable"
  echo "  6. Keep holding until device is detected (may take 5-10 seconds)"
  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo

  if ! confirm "Phone is OFF and USB DISCONNECTED - ready to proceed?"; then
    return 1
  fi

  log "Starting MTKClient NOW - quickly enter BROM mode!"
  log "Hold BOTH volume buttons and connect USB cable..."
  echo

  # Checked BEFORE the cd, so the early return needs no `cd -`. A subshell is
  # not an option here: this function exports BOOT_IMG to its caller.
  if [[ ! -d "$mtk_dir/venv" ]]; then
    error "MTKClient virtual environment not found. Run: $SCRIPT_NAME install-mtk"
    return 1
  fi

  local prev_dir="$PWD"
  cd "$mtk_dir" || {
    error "Cannot enter $mtk_dir"
    return 1
  }

  # shellcheck source=/dev/null
  source venv/bin/activate
  # BL9000 uses A/B partitions, so extract boot_a and vbmeta_a
  if python3 mtk.py r boot_a,vbmeta_a "$boot_a_img,$vbmeta_a_img"; then
    log "Boot_a and vbmeta_a extracted successfully!"

    # Copy boot_a.img to boot.img for Magisk compatibility
    cp "$boot_a_img" "$boot_img"
    BOOT_IMG="$boot_img"

    log "Boot image ready for patching: $BOOT_IMG"

    # Reset device
    log "Resetting device..."
    python3 mtk.py reset || warn "Failed to reset device, please reboot manually"

    # Deactivate venv if function exists
    type deactivate &> /dev/null && deactivate

    cd "$prev_dir" || true
    return 0
  else
    # Deactivate venv if function exists
    type deactivate &> /dev/null && deactivate

    error "Failed to extract boot image with MTKClient"
    cd "$prev_dir" || true
    return 1
  fi
}

extract_boot_image() {
  print_header "Extracting Boot Image"

  local boot_img="$WORK_DIR/boot.img"

  if [[ -n ${BOOT_IMG:-} && -f $BOOT_IMG ]]; then
    log "Using provided boot image: $BOOT_IMG"
    cp "$BOOT_IMG" "$boot_img"
    BOOT_IMG="$boot_img"
    return 0
  fi

  log "Attempting to extract boot image from device..."

  # Method 1: Try MTKClient first (best for MediaTek devices)
  if [[ -d "${WORK_DIR}/mtkclient" ]]; then
    log "Trying MTKClient extraction..."
    if extract_boot_with_mtkclient; then
      return 0
    fi
    warn "MTKClient extraction failed, trying ADB methods..."
  fi

  # Method 2: Try to pull boot partition directly via ADB
  local boot_partition
  boot_partition=$(adb shell "find /dev/block -name boot | head -n1" 2> /dev/null | tr -d '\r\n' || echo "")

  if [[ -n $boot_partition ]]; then
    log "Found boot partition: $boot_partition"
    if adb pull "$boot_partition" "$boot_img" 2> /dev/null; then
      log "Boot image extracted successfully"
      BOOT_IMG="$boot_img"
      return 0
    fi
  fi

  # Method 3: Try to get boot partition via by-name
  boot_partition=$(adb shell "ls /dev/block/by-name/boot*" 2> /dev/null | head -n1 | tr -d '\r\n' || echo "")

  if [[ -n $boot_partition ]]; then
    log "Found boot partition: $boot_partition"
    if adb shell "su -c 'dd if=$boot_partition of=/sdcard/boot.img'" 2> /dev/null &&
      adb pull /sdcard/boot.img "$boot_img" 2> /dev/null; then
      adb shell rm /sdcard/boot.img 2> /dev/null || true
      log "Boot image extracted successfully"
      BOOT_IMG="$boot_img"
      return 0
    fi
  fi

  error "Failed to extract boot image automatically."
  echo
  echo "Manual extraction options:"
  echo "1. Use MTKClient: $SCRIPT_NAME extract-mtk"
  echo "2. Extract boot.img from your device's firmware package"
  echo "3. Get boot.img from device manufacturer's official ROM"
  echo
  echo "Then run: $SCRIPT_NAME root --boot-img /path/to/boot.img"
  echo

  return 1
}

#!/bin/bash
# Device data backup before rooting.
#
# Sourced by root_bl9000.sh; split out to keep bl9000_deps.sh under the
# 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

backup_device_data() {
  print_header "Backing Up Device Data"

  local backup_dir
  backup_dir="${WORK_DIR}/backup_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$backup_dir"

  log "Backup directory: $backup_dir" # Check device connection first
  if ! adb get-state > /dev/null 2>&1; then
    error "Device not connected. Please connect your device first."
    return 1
  fi

  log "Starting comprehensive backup process..."

  # 1. Backup internal storage (DCIM, Pictures, Documents, Downloads, etc.)
  log "Backing up internal storage (this may take a while)..."
  local storage_dirs=("DCIM" "Pictures" "Documents" "Download" "Music" "Movies" "WhatsApp" "Telegram")

  for dir in "${storage_dirs[@]}"; do
    if adb shell "[ -d /sdcard/$dir ]" 2> /dev/null; then
      log "  → Backing up /sdcard/$dir..."
      if adb pull "/sdcard/$dir" "$backup_dir/$dir" 2>&1 | grep -v "^$"; then
        log "    ✓ $dir backed up successfully"
      else
        warn "    ⚠ Could not backup $dir (may be empty or inaccessible)"
      fi
    fi
  done

  # 2. Backup SMS/MMS (if possible)
  log "Backing up SMS/MMS database..."
  if adb shell "su -c 'cp /data/data/com.android.providers.telephony/databases/mmssms.db /sdcard/mmssms.db'" 2> /dev/null; then
    adb pull /sdcard/mmssms.db "$backup_dir/mmssms.db" 2> /dev/null && log "  ✓ SMS/MMS backed up"
    adb shell "rm /sdcard/mmssms.db" 2> /dev/null || true
  else
    warn "  ⚠ SMS/MMS backup requires root (skipping)"
  fi

  # 3. Backup contacts
  log "Backing up contacts..."
  if adb shell "su -c 'cp /data/data/com.android.providers.contacts/databases/contacts2.db /sdcard/contacts2.db'" 2> /dev/null; then
    adb pull /sdcard/contacts2.db "$backup_dir/contacts2.db" 2> /dev/null && log "  ✓ Contacts backed up"
    adb shell "rm /sdcard/contacts2.db" 2> /dev/null || true
  else
    warn "  ⚠ Contacts backup requires root (skipping)"
  fi

  # 4. Backup call logs
  log "Backing up call logs..."
  if adb shell "su -c 'cp /data/data/com.android.providers.contacts/databases/calllog.db /sdcard/calllog.db'" 2> /dev/null; then
    adb pull /sdcard/calllog.db "$backup_dir/calllog.db" 2> /dev/null && log "  ✓ Call logs backed up"
    adb shell "rm /sdcard/calllog.db" 2> /dev/null || true
  else
    warn "  ⚠ Call logs backup requires root (skipping)"
  fi

  # 5. Backup app list
  log "Backing up installed apps list..."
  adb shell "pm list packages -f" > "$backup_dir/installed_apps.txt"
  log "  ✓ App list saved to installed_apps.txt"

  # 6. Backup APKs for user-installed apps (optional, can be large)
  if confirm "Backup APK files for installed apps? (This can take a long time and use lots of space)"; then
    log "Backing up user-installed APKs..."
    local apk_dir="$backup_dir/apks"
    mkdir -p "$apk_dir"

    # Get user-installed packages
    local user_apps
    user_apps=$(adb shell "pm list packages -3 -f" | sed 's/package://' | cut -d'=' -f2)

    local count=0
    while IFS= read -r pkg; do
      if [[ -n $pkg ]]; then
        log "  → Backing up $pkg..."
        local apk_path
        apk_path=$(adb shell "pm path $pkg" | head -n1 | sed 's/package://')
        if [[ -n $apk_path ]]; then
          adb pull "$apk_path" "$apk_dir/${pkg}.apk" > /dev/null 2>&1 && count=$((count + 1))
        fi
      fi
    done <<< "$user_apps"

    log "  ✓ Backed up $count APK files"
  fi

  # 7. Full ADB backup (app data, if device supports it)
  log "Creating full ADB backup (app data)..."
  if confirm "Create full ADB backup? (You'll need to confirm on your device)"; then
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  On your phone: Tap 'Back up my data' when prompted"
    echo "  You can set a password or leave it blank"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo

    if adb backup -apk -shared -all -system -f "$backup_dir/full_backup.ab"; then
      log "  ✓ Full ADB backup completed"
      log "    Note: Restore with: adb restore full_backup.ab"
    else
      warn "  ⚠ ADB backup failed or was cancelled"
    fi
  fi

  # 8. Backup device info
  log "Saving device information..."
  {
    echo "Device Backup Information"
    echo "========================="
    echo "Date: $(date)"
    echo
    echo "Device Model: $(adb shell getprop ro.product.model | tr -d '\r\n')"
    echo "Android Version: $(adb shell getprop ro.build.version.release | tr -d '\r\n')"
    echo "Build Number: $(adb shell getprop ro.build.display.id | tr -d '\r\n')"
    echo "Security Patch: $(adb shell getprop ro.build.version.security_patch | tr -d '\r\n')"
    echo "Serial: $(adb shell getprop ro.serialno | tr -d '\r\n')"
    echo
    echo "Installed Apps:"
    adb shell "pm list packages -3" | sed 's/package:/  - /'
  } > "$backup_dir/device_info.txt"

  log "  ✓ Device info saved"

  # Summary
  local backup_size
  backup_size=$(du -sh "$backup_dir" 2> /dev/null | cut -f1 || echo "unknown")

  echo
  echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║            Backup Completed Successfully!             ║${NC}"
  echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
  echo
  log "Backup location: $backup_dir"
  log "Backup size: $backup_size"
  echo
  echo "What was backed up:"
  echo "  ✓ Photos (DCIM)"
  echo "  ✓ Pictures"
  echo "  ✓ Documents"
  echo "  ✓ Downloads"
  echo "  ✓ Music"
  echo "  ✓ Movies"
  echo "  ✓ WhatsApp data (if present)"
  echo "  ✓ Telegram data (if present)"
  echo "  ✓ Installed apps list"
  echo "  ✓ Device information"
  if [[ -f "$backup_dir/full_backup.ab" ]]; then
    echo "  ✓ Full app data backup"
  fi
  if [[ -d "$backup_dir/apks" ]]; then
    echo "  ✓ APK files"
  fi
  echo
  log "Keep this backup safe! You'll need it to restore your data after rooting."

  return 0
}

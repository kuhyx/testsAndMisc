#!/system/bin/sh
# Android Guardian Service - runs at boot
# This service:
# 1. Monitors and protects the hosts file
# 2. Blocks installation of forbidden apps
# 3. Prevents module from being disabled via Magisk UI
# 4. Can only be stopped via ADB with the correct command

MODDIR=${0%/*}
GUARDIAN_DIR="/data/adb/android_guardian"
LOG_FILE="$GUARDIAN_DIR/guardian.log"
BLOCKED_APPS_FILE="$GUARDIAN_DIR/blocked_apps.txt"
CONTROL_FILE="$GUARDIAN_DIR/control"
HOSTS_BACKUP="$GUARDIAN_DIR/hosts.backup"
MODULE_DIR="/data/adb/modules/android_guardian"
DISABLE_FILE="$MODULE_DIR/disable"
REMOVE_FILE="$MODULE_DIR/remove"

# Ensure guardian directory exists
mkdir -p "$GUARDIAN_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Initialize control file if not exists
[ ! -f "$CONTROL_FILE" ] && echo "ENABLED" > "$CONTROL_FILE"

log "=== Android Guardian starting ==="

# Enable wireless ADB on boot (persistent port 5555)
setprop service.adb.tcp.port 5555
stop adbd
start adbd
log "Wireless ADB enabled on port 5555"

# Function to check if guardian is enabled (via ADB control, not Magisk UI)
is_enabled() {
  [ "$(cat "$CONTROL_FILE" 2> /dev/null)" = "ENABLED" ]
}

# Function to protect module from being disabled via Magisk UI
protect_module() {
  # Remove disable file if someone tried to disable via Magisk
  if [ -f "$DISABLE_FILE" ]; then
    log "Module disable attempt detected via Magisk UI! Re-enabling..."
    rm -f "$DISABLE_FILE"
    log "Module re-enabled"
  fi

  # Remove remove file if someone tried to uninstall via Magisk
  if [ -f "$REMOVE_FILE" ]; then
    log "Module removal attempt detected via Magisk UI! Blocking..."
    rm -f "$REMOVE_FILE"
    log "Module removal blocked"
  fi
}

# Function to restore hosts file if tampered
protect_hosts() {
  if [ -f "$HOSTS_BACKUP" ]; then
    current_hash=$(md5sum /system/etc/hosts 2> /dev/null | cut -d' ' -f1)
    backup_hash=$(md5sum "$HOSTS_BACKUP" 2> /dev/null | cut -d' ' -f1)

    if [ "$current_hash" != "$backup_hash" ]; then
      log "Hosts file tampering detected! Restoring..."
      cp "$HOSTS_BACKUP" "$MODDIR/system/etc/hosts"
      log "Hosts file restored"
    fi
  fi
}

# Function to uninstall blocked apps
check_blocked_apps() {
  if [ ! -f "$BLOCKED_APPS_FILE" ]; then
    return
  fi

  while IFS= read -r package || [ -n "$package" ]; do
    # Skip comments and empty lines
    case "$package" in
      \#* | "") continue ;;
    esac

    # Check if package is installed
    if pm list packages 2> /dev/null | grep -q "package:$package"; then
      log "Blocked app detected: $package - Uninstalling..."
      pm uninstall "$package" 2> /dev/null && log "Uninstalled: $package" || log "Failed to uninstall: $package"
    fi
  done < "$BLOCKED_APPS_FILE"
}

# Main monitoring loop - runs every 5 seconds for faster protection
while true; do
  # ALWAYS protect module from UI disabling (even if guardian is "disabled" via ADB)
  # This ensures only ADB can control the guardian
  protect_module

  if is_enabled; then
    protect_hosts
    check_blocked_apps
  fi

  # Check every 5 seconds (faster response to disable attempts)
  sleep 5
done &

log "Guardian service started (PID: $!)"

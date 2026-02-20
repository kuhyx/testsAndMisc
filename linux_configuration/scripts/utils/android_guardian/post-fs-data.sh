#!/system/bin/sh
# Runs early in boot - set up hosts file and start watchdog
# MODDIR is set by Magisk and points to this module's directory
GUARDIAN_DIR="/data/adb/android_guardian"
# shellcheck disable=SC2034  # Used for documentation; heredoc defines its own
MODULE_DIR="/data/adb/modules/android_guardian"
WATCHDOG_SCRIPT="$GUARDIAN_DIR/watchdog.sh"

mkdir -p "$GUARDIAN_DIR"

# Log that we're starting
echo "[$(date '+%Y-%m-%d %H:%M:%S')] post-fs-data: Guardian module loading" >>"$GUARDIAN_DIR/guardian.log"

# Create persistent watchdog script that runs independently of module state
cat >"$WATCHDOG_SCRIPT" <<'WATCHDOG'
#!/system/bin/sh
# Secondary watchdog - runs independently of module state
# Even if module is "disabled" in Magisk UI, this keeps running and undoes it
GUARDIAN_DIR="/data/adb/android_guardian"
MODULE_DIR="/data/adb/modules/android_guardian"
LOG_FILE="$GUARDIAN_DIR/watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG_FILE"
}

log "=== Watchdog starting ==="

while true; do
    # Protect module from Magisk UI disable/remove
    if [ -f "$MODULE_DIR/disable" ]; then
        log "ALERT: Module disable detected via Magisk UI - removing disable flag"
        rm -f "$MODULE_DIR/disable"
    fi

    if [ -f "$MODULE_DIR/remove" ]; then
        log "ALERT: Module removal detected via Magisk UI - removing remove flag"
        rm -f "$MODULE_DIR/remove"
    fi

    # Also protect the hosts file directly
    CONTROL_FILE="$GUARDIAN_DIR/control"
    if [ "$(cat "$CONTROL_FILE" 2>/dev/null)" = "ENABLED" ]; then
        if [ -f "$GUARDIAN_DIR/hosts.backup" ] && [ -f "$MODULE_DIR/system/etc/hosts" ]; then
            current_hash=$(md5sum "$MODULE_DIR/system/etc/hosts" 2>/dev/null | cut -d' ' -f1)
            backup_hash=$(md5sum "$GUARDIAN_DIR/hosts.backup" 2>/dev/null | cut -d' ' -f1)

            if [ "$current_hash" != "$backup_hash" ]; then
                log "ALERT: Hosts tampering detected - restoring"
                cp "$GUARDIAN_DIR/hosts.backup" "$MODULE_DIR/system/etc/hosts"
            fi
        fi
    fi

    sleep 3
done
WATCHDOG

chmod 755 "$WATCHDOG_SCRIPT"

# Start watchdog as a separate background process
nohup sh "$WATCHDOG_SCRIPT" >/dev/null 2>&1 &
echo "[$(date '+%Y-%m-%d %H:%M:%S')] post-fs-data: Watchdog started" >>"$GUARDIAN_DIR/guardian.log"

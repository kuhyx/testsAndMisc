#!/system/bin/sh
# Android Guardian Service - runs at boot
# This service:
# 1. Monitors and protects the hosts file
# 2. Blocks installation of forbidden apps
# 3. Can only be stopped via ADB with the correct command

MODDIR=${0%/*}
GUARDIAN_DIR="/data/adb/android_guardian"
LOG_FILE="$GUARDIAN_DIR/guardian.log"
BLOCKED_APPS_FILE="$GUARDIAN_DIR/blocked_apps.txt"
CONTROL_FILE="$GUARDIAN_DIR/control"
HOSTS_BACKUP="$GUARDIAN_DIR/hosts.backup"

# Ensure guardian directory exists
mkdir -p "$GUARDIAN_DIR"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG_FILE"
}

# Initialize control file if not exists
[ ! -f "$CONTROL_FILE" ] && echo "ENABLED" >"$CONTROL_FILE"

log "=== Android Guardian starting ==="

# Function to check if guardian is enabled
is_enabled() {
	[ "$(cat "$CONTROL_FILE" 2>/dev/null)" = "ENABLED" ]
}

# Function to restore hosts file if tampered
protect_hosts() {
	if [ -f "$HOSTS_BACKUP" ]; then
		current_hash=$(md5sum /system/etc/hosts 2>/dev/null | cut -d' ' -f1)
		backup_hash=$(md5sum "$HOSTS_BACKUP" 2>/dev/null | cut -d' ' -f1)

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
		if pm list packages 2>/dev/null | grep -q "package:$package"; then
			log "Blocked app detected: $package - Uninstalling..."
			pm uninstall "$package" 2>/dev/null && log "Uninstalled: $package" || log "Failed to uninstall: $package"
		fi
	done <"$BLOCKED_APPS_FILE"
}

# Main monitoring loop
while true; do
	if is_enabled; then
		protect_hosts
		check_blocked_apps
	fi

	# Check every 30 seconds
	sleep 30
done &

log "Guardian service started (PID: $!)"

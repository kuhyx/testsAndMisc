#!/bin/bash
# The install, status, disable and app-blocking subcommands.
#
# Sourced by update_android_hosts.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode.

# Install/update the guardian module
cmd_install() {
	ensure_device_ready

	local module_zip
	module_zip=$(build_module)

	log "Pushing module to device..."
	adb push "$module_zip" /sdcard/android_guardian.zip || die "Failed to push module"

	log "Installing module..."
	adb shell "su -c 'mkdir -p $MODULE_DEST'" || die "Failed to create module directory"
	adb shell "su -c 'cd $MODULE_DEST && unzip -o /sdcard/android_guardian.zip'" || die "Failed to extract module"
	adb shell "su -c 'chmod 755 $MODULE_DEST/*.sh'"
	adb shell "su -c 'rm /sdcard/android_guardian.zip'"

	# Set up guardian data directory
	log "Setting up guardian data..."
	adb shell "su -c 'mkdir -p $GUARDIAN_DATA_DIR'"
	adb shell "su -c 'echo ENABLED > $GUARDIAN_DATA_DIR/control'"

	# Copy blocked apps list
	adb push "$GUARDIAN_MODULE_DIR/blocked_apps.txt" /sdcard/blocked_apps.txt || die "Failed to push blocked apps list"
	adb shell "su -c 'cp /sdcard/blocked_apps.txt $GUARDIAN_DATA_DIR/blocked_apps.txt'"
	adb shell "su -c 'rm /sdcard/blocked_apps.txt'"

	# Create hosts backup for tamper protection
	adb shell "su -c 'cp $MODULE_DEST/system/etc/hosts $GUARDIAN_DATA_DIR/hosts.backup'"

	# Immediately uninstall any currently installed blocked apps
	log "Checking for blocked apps to remove..."
	uninstall_blocked_apps

	echo ""
	echo "=========================================="
	echo "  ✓ Android Guardian installed!"
	echo "=========================================="
	echo ""
	echo "Features enabled:"
	echo "  • Hosts-based ad/tracker blocking"
	echo "  • App installation blocking"
	echo "  • Tamper protection"
	echo ""
	echo "⚠️  This can ONLY be controlled via ADB:"
	echo "  Disable: $0 disable"
	echo "  Enable:  $0 enable"
	echo "  Status:  $0 status"
	echo ""
	echo "Reboot your device to activate the module."
	echo ""
}

# Uninstall currently installed blocked apps
uninstall_blocked_apps() {
	local blocked_apps
	blocked_apps=$(grep -v '^#' "$GUARDIAN_MODULE_DIR/blocked_apps.txt" | grep -v '^$' || true)

	for package in $blocked_apps; do
		if adb shell "pm list packages" 2>/dev/null | grep -q "package:$package"; then
			log "Uninstalling blocked app: $package"
			adb shell "pm uninstall $package" 2>/dev/null || true
		fi
	done
}

# Show status
cmd_status() {
	ensure_device_ready

	echo ""
	echo "=== Android Guardian Status ==="
	echo ""

	# Check if module is installed
	if adb shell "su -c 'test -d $MODULE_DEST'" 2>/dev/null; then
		echo "Module: INSTALLED"
	else
		echo "Module: NOT INSTALLED"
		return
	fi

	# Check control status
	local status
	status=$(adb shell "su -c 'cat $GUARDIAN_DATA_DIR/control 2>/dev/null || echo UNKNOWN'" | tr -d '\r')
	echo "Status: $status"

	# Check if module is "disabled" in Magisk UI (should be auto-fixed by watchdog)
	local magisk_disabled
	if adb shell "su -c 'test -f $MODULE_DEST/disable'" 2>/dev/null; then
		magisk_disabled="YES (watchdog should fix this)"
	else
		magisk_disabled="No"
	fi
	echo "Magisk UI disabled: $magisk_disabled"

	# Check if watchdog is running
	local watchdog_running
	watchdog_running=$(adb shell "su -c 'pgrep -f watchdog.sh 2>/dev/null | wc -l'" | tr -d '\r')
	if [ "$watchdog_running" -gt 0 ] 2>/dev/null; then
		echo "Watchdog: RUNNING ($watchdog_running processes)"
	else
		echo "Watchdog: NOT RUNNING (reboot phone to start)"
	fi

	# Check hosts file
	local hosts_entries
	hosts_entries=$(adb shell "su -c 'grep -c \"^0.0.0.0\" /system/etc/hosts 2>/dev/null || echo 0'" | tr -d '\r')
	echo "Blocked domains: $hosts_entries"

	# Check blocked apps count
	local blocked_count
	blocked_count=$(adb shell "su -c 'grep -v \"^#\" $GUARDIAN_DATA_DIR/blocked_apps.txt 2>/dev/null | grep -v \"^$\" | wc -l || echo 0'" | tr -d '\r')
	echo "Blocked app rules: $blocked_count packages"

	echo ""
	echo "Protection: Module cannot be disabled from Magisk UI"
	echo "            Only controllable via: $0 disable/enable"
	echo ""
}

# Disable guardian
cmd_disable() {
	ensure_device_ready

	log "Disabling Android Guardian..."
	adb shell "su -c 'echo DISABLED > $GUARDIAN_DATA_DIR/control'" || die "Failed to disable guardian"

	echo ""
	echo "✓ Guardian DISABLED"
	echo "  Hosts blocking still active until reboot"
	echo "  App blocking service paused"
	echo ""
	echo "To re-enable: $0 enable"
	echo ""
}

# Enable guardian
cmd_enable() {
	ensure_device_ready

	log "Enabling Android Guardian..."
	adb shell "su -c 'echo ENABLED > $GUARDIAN_DATA_DIR/control'" || die "Failed to enable guardian"

	echo ""
	echo "✓ Guardian ENABLED"
	echo ""
}

# Uninstall module
cmd_uninstall() {
	ensure_device_ready

	# Check if disabled first
	local status
	status=$(adb shell "su -c 'cat $GUARDIAN_DATA_DIR/control 2>/dev/null || echo ENABLED'" | tr -d '\r')

	if [[ $status != "DISABLED" ]]; then
		echo ""
		echo "⚠️  Guardian must be disabled before uninstalling!"
		echo "   Run: $0 disable"
		echo "   Then: $0 uninstall"
		echo ""
		exit 1
	fi

	log "Removing Android Guardian..."
	adb shell "su -c 'rm -rf $MODULE_DEST'"
	adb shell "su -c 'rm -rf $GUARDIAN_DATA_DIR'"

	echo ""
	echo "✓ Guardian uninstalled"
	echo "  Reboot to remove hosts blocking"
	echo ""
}

# Show logs
cmd_logs() {
	ensure_device_ready

	echo "=== Guardian Logs ==="
	adb shell "su -c 'cat $GUARDIAN_DATA_DIR/guardian.log 2>/dev/null || echo \"No logs yet\"'"
}

# Block an app
cmd_block_app() {
	local package="${1:-}"

	if [[ -z $package ]]; then
		echo "Usage: $0 block-app <package.name>"
		echo "Example: $0 block-app com.ubercab.eats"
		exit 1
	fi

	ensure_device_ready

	log "Adding $package to block list..."
	adb shell "su -c 'echo \"$package\" >> $GUARDIAN_DATA_DIR/blocked_apps.txt'"

	# Also add to local file
	echo "$package" >>"$GUARDIAN_MODULE_DIR/blocked_apps.txt"

	# Try to uninstall if currently installed
	if adb shell "pm list packages" 2>/dev/null | grep -q "package:$package"; then
		log "Uninstalling $package..."
		adb shell "pm uninstall $package" 2>/dev/null || true
	fi

	echo "✓ $package added to block list"
}

# Unblock an app
cmd_unblock_app() {
	local package="${1:-}"

	if [[ -z $package ]]; then
		echo "Usage: $0 unblock-app <package.name>"
		exit 1
	fi

	ensure_device_ready

	log "Removing $package from block list..."
	adb shell "su -c 'grep -v \"^$package\$\" $GUARDIAN_DATA_DIR/blocked_apps.txt > $GUARDIAN_DATA_DIR/blocked_apps.tmp && mv $GUARDIAN_DATA_DIR/blocked_apps.tmp $GUARDIAN_DATA_DIR/blocked_apps.txt'"

	# Also remove from local file
	grep -v "^$package$" "$GUARDIAN_MODULE_DIR/blocked_apps.txt" >"$GUARDIAN_MODULE_DIR/blocked_apps.tmp" && mv "$GUARDIAN_MODULE_DIR/blocked_apps.tmp" "$GUARDIAN_MODULE_DIR/blocked_apps.txt"

	echo "✓ $package removed from block list"
}

# List blocked apps
cmd_list_blocked() {
	ensure_device_ready

	echo "=== Blocked Apps ==="
	adb shell "su -c 'cat $GUARDIAN_DATA_DIR/blocked_apps.txt 2>/dev/null'" | grep -v "^#" | grep -v "^$" || echo "No blocked apps"
}

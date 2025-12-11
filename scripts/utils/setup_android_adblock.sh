#!/bin/bash

set -euo pipefail

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"
# shellcheck source=../lib/android.sh
source "$SCRIPT_DIR/../lib/android.sh"

# Re-run with sudo if needed for reading /etc/hosts
require_hosts_readable "$@"

WORK_DIR="$ANDROID_WORK_DIR"

install_adaway() {
	print_header "Installing AdAway"

	local adaway_apk="$WORK_DIR/adaway.apk"
	local adaway_url="https://github.com/AdAway/AdAway/releases/latest/download/AdAway.apk"

	if [[ ! -f $adaway_apk ]]; then
		log "Downloading AdAway APK..."
		curl -L -o "$adaway_apk" "$adaway_url" || die "Failed to download AdAway"
	else
		log "AdAway APK already downloaded"
	fi

	log "Installing AdAway..."
	if adb install -r "$adaway_apk" 2>&1 | grep -q "Success"; then
		log "AdAway installed successfully"
	else
		warn "AdAway installation may have failed or already installed"
	fi
}

setup_systemless_hosts() {
	print_header "Setting up Systemless Hosts"

	log "Installing Systemless Hosts module..."

	# Create systemless hosts module directory
	adb shell "su -c 'mkdir -p /data/adb/modules/systemless_hosts/system/etc'" || die "Failed to create module directory"

	# Create module.prop
	cat >"$WORK_DIR/module.prop" <<'EOF'
id=systemless_hosts
name=Systemless Hosts
version=1.0
versionCode=1
author=Custom
description=Custom hosts file from StevenBlack with extensions
EOF

	adb push "$WORK_DIR/module.prop" /sdcard/module.prop
	adb shell "su -c 'cp /sdcard/module.prop /data/adb/modules/systemless_hosts/'" || die "Failed to create module.prop"
	adb shell "su -c 'rm /sdcard/module.prop'"

	log "Module structure created"
}

push_hosts_file() {
	print_header "Pushing Custom Hosts File"

	local hosts_file="$WORK_DIR/hosts"

	# Use the StevenBlack cache or generate from /etc/hosts
	if [[ -f /etc/hosts.stevenblack ]]; then
		log "Using StevenBlack hosts cache..."
		cp /etc/hosts.stevenblack "$hosts_file"
	elif [[ -f /etc/hosts ]]; then
		log "Using current /etc/hosts..."
		cp /etc/hosts "$hosts_file"
	else
		die "No hosts file found"
	fi

	# Show stats
	local total_entries
	total_entries=$(grep -c "^0\.0\.0\.0 " "$hosts_file" || echo 0)
	log "Hosts file contains $total_entries blocked domains"

	log "Pushing hosts file to device..."
	adb push "$hosts_file" /sdcard/hosts || die "Failed to push hosts file"

	log "Installing hosts file systemlessly..."
	adb shell "su -c 'cp /sdcard/hosts /data/adb/modules/systemless_hosts/system/etc/hosts'" || die "Failed to install hosts file"
	adb shell "su -c 'chmod 644 /data/adb/modules/systemless_hosts/system/etc/hosts'" || die "Failed to set permissions"
	adb shell "su -c 'rm /sdcard/hosts'"

	log "Hosts file installed successfully"
	log "Total blocked domains: $total_entries"
}

enable_module() {
	print_header "Enabling Systemless Hosts Module"

	log "Removing disable flag if present..."
	adb shell "su -c 'rm -f /data/adb/modules/systemless_hosts/disable'" 2>/dev/null || true
	adb shell "su -c 'rm -f /data/adb/modules/systemless_hosts/remove'" 2>/dev/null || true

	log "Module enabled"

	echo
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo "  REBOOT REQUIRED"
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo
	echo "The systemless hosts module requires a reboot to take effect."
	echo
	read -p "Reboot device now? [y/N]: " -n 1 -r
	echo

	if [[ $REPLY =~ ^[Yy]$ ]]; then
		log "Rebooting device..."
		adb reboot
		log "Device rebooting. Wait for boot to complete."
	else
		warn "Remember to reboot manually for changes to take effect!"
	fi
}

verify_hosts() {
	print_header "Verifying Hosts Installation"

	log "Waiting for device to boot..."
	sleep 5
	adb wait-for-device
	sleep 10

	log "Checking if hosts file is active..."
	local test_domain="doubleclick.net"
	local result
	result=$(adb shell "su -c 'cat /system/etc/hosts | grep -c $test_domain'" 2>/dev/null || echo "0")

	if [[ $result -gt 0 ]]; then
		log "✓ Hosts file is active and blocking domains"
	else
		warn "Could not verify hosts file, but module should be installed"
	fi
}

main() {
	print_header "Android Ad Blocking Setup"

	check_device
	check_root

	echo "This will:"
	echo "  1. Install AdAway app (optional GUI management)"
	echo "  2. Create systemless hosts module"
	echo "  3. Push your custom hosts file (StevenBlack with extensions)"
	echo "  4. Enable the module and reboot"
	echo
	read -p "Continue? [y/N]: " -n 1 -r
	echo

	if [[ ! $REPLY =~ ^[Yy]$ ]]; then
		log "Cancelled by user"
		exit 0
	fi

	install_adaway
	setup_systemless_hosts
	push_hosts_file
	enable_module

	log "Setup complete!"
	log "After reboot, ads should be blocked system-wide"
	log "You can manage hosts in the AdAway app or by updating the module"
}

main "$@"

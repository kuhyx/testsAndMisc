#!/bin/bash
# update_android_hosts.sh - Deploy Android Guardian (hosts blocking + app blocker)
# This creates a persistent protection that can ONLY be controlled via ADB
set -euo pipefail

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"
# shellcheck source=../lib/android.sh
source "$SCRIPT_DIR/../lib/android.sh"

GUARDIAN_MODULE_DIR="$SCRIPT_DIR/android_guardian"
GUARDIAN_DATA_DIR="/data/adb/android_guardian"
MODULE_DEST="/data/adb/modules/android_guardian"

# Ensure android-tools (adb) is installed
ensure_adb_installed() {
	if command -v adb &>/dev/null; then
		return 0
	fi

	log "adb not found, installing android-tools..."

	if command -v pacman &>/dev/null; then
		sudo pacman -S --noconfirm android-tools || die "Failed to install android-tools"
	elif command -v apt-get &>/dev/null; then
		sudo apt-get update && sudo apt-get install -y adb || die "Failed to install adb"
	elif command -v dnf &>/dev/null; then
		sudo dnf install -y android-tools || die "Failed to install android-tools"
	else
		die "adb not found and could not determine package manager. Please install android-tools manually."
	fi

	# Verify installation
	if ! command -v adb &>/dev/null; then
		die "adb installation failed"
	fi

	log "android-tools installed successfully"
}

show_usage() {
	cat <<EOF
Usage: $(basename "$0") [COMMAND]

Commands:
  install       Install/update Android Guardian module (default)
  status        Show guardian status
  disable       Temporarily disable guardian (requires ADB)
  enable        Re-enable guardian (requires ADB)
  uninstall     Remove guardian module (requires ADB + disable first)
  logs          Show guardian logs
  block-app     Add an app to block list
  unblock-app   Remove an app from block list
  list-blocked  Show blocked apps list
  
  pair          Pair with device over WiFi (Android 11+, no USB needed)
  connect       Connect to already-paired device over WiFi
  disconnect    Disconnect wireless ADB

Android Guardian provides:
  - Persistent hosts-based ad/tracker blocking
  - Automatic uninstallation of forbidden apps (browsers, food delivery, etc.)
  - Protection that can ONLY be controlled via ADB connection

The module CANNOT be disabled from the Magisk app on the phone.
You MUST connect the phone to a PC and use this script to control it.

Wireless Setup (Android 11+):
  1. On phone: Settings > Developer Options > Wireless debugging > Enable
  2. Tap "Pair device with pairing code" to get IP:port and code
  3. Run: $0 pair
  4. Future connections: $0 connect

EOF
}

# Wireless ADB connection file
WIRELESS_CONFIG="$HOME/.config/android_guardian_wireless"

# Discover Android devices on the network using mDNS
discover_android_device() {
	local found_address=""

	# Ensure avahi-browse is available
	if ! command -v avahi-browse &>/dev/null; then
		if command -v pacman &>/dev/null; then
			echo "Installing avahi for device discovery..." >&2
			sudo pacman -S --noconfirm avahi nss-mdns &>/dev/null || true
			sudo systemctl enable --now avahi-daemon &>/dev/null || true
		elif command -v apt-get &>/dev/null; then
			sudo apt-get install -y avahi-utils &>/dev/null || true
		fi
	fi

	if command -v avahi-browse &>/dev/null; then
		echo "Scanning for Android devices (5 seconds)..." >&2

		# Android wireless debugging advertises as _adb-tls-connect._tcp
		local discovery_result
		discovery_result=$(timeout 5 avahi-browse -rpt _adb-tls-connect._tcp 2>/dev/null | grep "^=" | head -1)

		if [[ -n "$discovery_result" ]]; then
			# Parse: =;eth0;IPv4;adb-...;_adb-tls-connect._tcp;local;hostname.local;192.168.x.x;port;...
			local ip port
			ip=$(echo "$discovery_result" | cut -d';' -f8)
			port=$(echo "$discovery_result" | cut -d';' -f9)

			if [[ -n "$ip" && -n "$port" ]]; then
				found_address="$ip:$port"
				echo "✓ Found device: $found_address" >&2
			fi
		fi
	fi

	# Fallback: try adb's mdns discovery
	if [[ -z "$found_address" ]]; then
		echo "Trying adb mdns discovery..." >&2

		# adb can discover devices via mdns
		local mdns_result
		mdns_result=$(timeout 5 adb mdns services 2>/dev/null | grep -E "adb-tls-connect|_adb\._tcp" | head -1)

		if [[ -n "$mdns_result" ]]; then
			# Try to extract IP:port from the result
			local service_name
			service_name=$(echo "$mdns_result" | awk '{print $1}')
			if [[ -n "$service_name" ]]; then
				# Try connecting via service name
				echo "Found service: $service_name" >&2
			fi
		fi
	fi

	# Return found address (or empty)
	echo "$found_address"
}

# Pair with device over WiFi (Android 11+)
cmd_pair() {
	ensure_adb_installed

	echo ""
	echo "=== Wireless ADB Pairing (Android 11+) ==="
	echo ""
	echo "On your phone:"
	echo "  1. Go to Settings > Developer Options > Wireless debugging"
	echo "  2. Enable Wireless debugging"
	echo "  3. Tap 'Pair device with pairing code'"
	echo "  4. Note the IP:port and pairing code shown"
	echo ""

	read -rp "Enter pairing IP:port (e.g., 192.168.1.100:37123): " pair_address
	read -rp "Enter pairing code: " pair_code

	if [[ -z "$pair_address" || -z "$pair_code" ]]; then
		die "Pairing address and code are required"
	fi

	log "Pairing with device at $pair_address..."
	if adb pair "$pair_address" "$pair_code"; then
		echo ""
		echo "✓ Pairing successful!"
		echo ""
		echo "Now get the connection address:"
		echo "  On phone: Wireless debugging screen shows IP:port under 'IP address & Port'"
		echo "  (This is DIFFERENT from the pairing port)"
		echo ""
		read -rp "Enter connection IP:port (e.g., 192.168.1.100:41567): " connect_address

		if [[ -n "$connect_address" ]]; then
			# Save for future connections
			mkdir -p "$(dirname "$WIRELESS_CONFIG")"
			echo "$connect_address" >"$WIRELESS_CONFIG"
			log "Saved connection address for future use"

			# Connect now
			cmd_connect
		fi
	else
		die "Pairing failed. Make sure the code is correct and you're on the same network."
	fi
}

# Connect to already-paired device
cmd_connect() {
	ensure_adb_installed

	local connect_address=""

	# Check for saved address
	if [[ -f "$WIRELESS_CONFIG" ]]; then
		connect_address=$(cat "$WIRELESS_CONFIG")
		log "Using saved address: $connect_address"
	fi

	# Try auto-discovery if no saved address
	if [[ -z "$connect_address" ]]; then
		echo ""
		log "Searching for Android devices on network..."
		connect_address=$(discover_android_device)
	fi

	# Manual fallback
	if [[ -z "$connect_address" ]]; then
		echo ""
		echo "Auto-discovery failed. Enter address manually."
		echo "On phone: Settings > Developer Options > Wireless debugging"
		echo "Look for IP address & Port (NOT the pairing port)"
		echo ""
		read -rp "Enter connection IP:port (e.g., 192.168.1.100:41567): " connect_address

		if [[ -z "$connect_address" ]]; then
			die "Connection address is required"
		fi
	fi

	# Save for future
	mkdir -p "$(dirname "$WIRELESS_CONFIG")"
	echo "$connect_address" >"$WIRELESS_CONFIG"

	log "Connecting to $connect_address..."
	if adb connect "$connect_address" | grep -q "connected"; then
		echo ""
		echo "✓ Connected to device wirelessly!"
		echo ""

		# Verify connection
		if adb devices | grep -q "$connect_address"; then
			echo "Device ready. You can now run other commands."
		fi
	else
		echo ""
		echo "Connection failed. Possible issues:"
		echo "  - Wireless debugging not enabled on phone"
		echo "  - Phone and PC not on same WiFi network"
		echo "  - Port changed (check Wireless debugging screen)"
		echo "  - May need to pair first: $0 pair"
		echo ""
		# Clear saved config since it failed
		rm -f "$WIRELESS_CONFIG"
		exit 1
	fi
}

# Disconnect wireless ADB
cmd_disconnect() {
	ensure_adb_installed

	log "Disconnecting all wireless devices..."
	adb disconnect
	echo "✓ Disconnected"
}

# Check device connection and root
ensure_device_ready() {
	ensure_adb_installed

	# Check if any device is connected
	if ! adb devices | grep -qE "device$|:.*device$"; then
		echo ""
		echo "No device connected!"
		echo ""
		echo "Options:"
		echo "  1. Connect USB cable with debugging enabled"
		echo "  2. Use wireless: $0 pair (first time) or $0 connect"
		echo ""

		# Check if we have a saved wireless config
		if [[ -f "$WIRELESS_CONFIG" ]]; then
			read -rp "Try connecting to saved wireless device? [Y/n]: " try_wireless
			if [[ "${try_wireless,,}" != "n" ]]; then
				cmd_connect
			else
				exit 1
			fi
		else
			exit 1
		fi
	fi

	check_adb_device
	check_adb_root
}

# Build the module zip
build_module() {
	local tmp_dir="$WORK_DIR/guardian_module"
	local module_zip="$WORK_DIR/android_guardian.zip"

	echo "[BUILD] Building Android Guardian module..." >&2

	rm -rf "$tmp_dir"
	mkdir -p "$tmp_dir/system/etc"

	# Copy module files
	cp "$GUARDIAN_MODULE_DIR/module.prop" "$tmp_dir/"
	cp "$GUARDIAN_MODULE_DIR/service.sh" "$tmp_dir/"
	cp "$GUARDIAN_MODULE_DIR/post-fs-data.sh" "$tmp_dir/"
	cp "$GUARDIAN_MODULE_DIR/uninstall.sh" "$tmp_dir/"

	# Build hosts file
	local hosts_file="$tmp_dir/system/etc/hosts"
	if [[ -f /etc/hosts.stevenblack ]]; then
		echo "[BUILD] Using StevenBlack hosts cache..." >&2
		cp /etc/hosts.stevenblack "$hosts_file"
	elif [[ -f /etc/hosts ]]; then
		echo "[BUILD] Using /etc/hosts..." >&2
		cp /etc/hosts "$hosts_file"
	else
		die "No hosts file found"
	fi

	# Append custom blocking entries
	cat >>"$hosts_file" <<'CUSTOM_EOF'

# ============================================
# Custom blocking entries - Android Guardian
# ============================================

# YouTube
0.0.0.0 youtube.com
0.0.0.0 www.youtube.com
0.0.0.0 m.youtube.com
0.0.0.0 youtu.be
0.0.0.0 youtube-nocookie.com
0.0.0.0 www.youtube-nocookie.com
0.0.0.0 youtubei.googleapis.com
0.0.0.0 youtube.googleapis.com
0.0.0.0 yt3.ggpht.com
0.0.0.0 ytimg.com
0.0.0.0 i.ytimg.com
0.0.0.0 s.ytimg.com
0.0.0.0 i9.ytimg.com
0.0.0.0 googlevideo.com

# Discord (media only - voice chat allowed)
0.0.0.0 cdn.discordapp.com
0.0.0.0 media.discordapp.net
0.0.0.0 images-ext-1.discordapp.net
0.0.0.0 images-ext-2.discordapp.net
0.0.0.0 tenor.com
0.0.0.0 giphy.com

# Food Delivery Services
0.0.0.0 pyszne.pl
0.0.0.0 www.pyszne.pl
0.0.0.0 glovo.com
0.0.0.0 www.glovo.com
0.0.0.0 bolt.eu
0.0.0.0 food.bolt.eu
0.0.0.0 wolt.com
0.0.0.0 www.wolt.com
0.0.0.0 ubereats.com
0.0.0.0 www.ubereats.com
0.0.0.0 deliveroo.com
0.0.0.0 www.deliveroo.com
0.0.0.0 foodpanda.com
0.0.0.0 www.foodpanda.com
0.0.0.0 grubhub.com
0.0.0.0 www.grubhub.com
0.0.0.0 doordash.com
0.0.0.0 www.doordash.com
0.0.0.0 justeat.com
0.0.0.0 www.justeat.com

# Fast Food
0.0.0.0 mcdonalds.com
0.0.0.0 www.mcdonalds.com
0.0.0.0 mcdonalds.pl
0.0.0.0 www.mcdonalds.pl
0.0.0.0 kfc.com
0.0.0.0 www.kfc.com
0.0.0.0 kfc.pl
0.0.0.0 www.kfc.pl
0.0.0.0 burgerking.com
0.0.0.0 www.burgerking.com
0.0.0.0 pizzahut.com
0.0.0.0 www.pizzahut.com
0.0.0.0 dominos.com
0.0.0.0 www.dominos.com
CUSTOM_EOF

	local total_entries
	total_entries=$(grep -c "^0\.0\.0\.0 " "$hosts_file" || echo 0)
	echo "[BUILD] Hosts file contains $total_entries blocked domains" >&2

	# Create zip
	(cd "$tmp_dir" && zip -r "$module_zip" . -x "*.DS_Store") >/dev/null

	echo "$module_zip"
}

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

	if [[ "$status" != "DISABLED" ]]; then
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

	if [[ -z "$package" ]]; then
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

	if [[ -z "$package" ]]; then
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

# Main
# Initialize Android script (handles sudo, sets WORK_DIR)
init_android_script "$@"

COMMAND="${1:-install}"
shift || true

case "$COMMAND" in
install)
	cmd_install
	;;
status)
	cmd_status
	;;
disable)
	cmd_disable
	;;
enable)
	cmd_enable
	;;
uninstall)
	cmd_uninstall
	;;
logs)
	cmd_logs
	;;
block-app)
	cmd_block_app "$@"
	;;
unblock-app)
	cmd_unblock_app "$@"
	;;
list-blocked)
	cmd_list_blocked
	;;
pair)
	cmd_pair
	;;
connect)
	cmd_connect
	;;
disconnect)
	cmd_disconnect
	;;
-h | --help | help)
	show_usage
	;;
*)
	echo "Unknown command: $COMMAND"
	show_usage
	exit 1
	;;
esac

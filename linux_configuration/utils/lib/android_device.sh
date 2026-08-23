#!/bin/bash
# Device discovery, pairing and connection.
#
# Sourced by update_android_hosts.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode.

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

		if [[ -n $discovery_result ]]; then
			# Parse: =;eth0;IPv4;adb-...;_adb-tls-connect._tcp;local;hostname.local;192.168.x.x;port;...
			local ip port
			ip=$(echo "$discovery_result" | cut -d';' -f8)
			port=$(echo "$discovery_result" | cut -d';' -f9)

			if [[ -n $ip && -n $port ]]; then
				found_address="$ip:$port"
				echo "✓ Found device: $found_address" >&2
			fi
		fi
	fi

	# Fallback: try adb's mdns discovery
	if [[ -z $found_address ]]; then
		echo "Trying adb mdns discovery..." >&2

		# adb can discover devices via mdns
		local mdns_result
		mdns_result=$(timeout 5 adb mdns services 2>/dev/null | grep -E "adb-tls-connect|_adb\._tcp" | head -1)

		if [[ -n $mdns_result ]]; then
			# Try to extract IP:port from the result
			local service_name
			service_name=$(echo "$mdns_result" | awk '{print $1}')
			if [[ -n $service_name ]]; then
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

	if [[ -z $pair_address || -z $pair_code ]]; then
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

		if [[ -n $connect_address ]]; then
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
	if [[ -f $WIRELESS_CONFIG ]]; then
		connect_address=$(cat "$WIRELESS_CONFIG")
		log "Using saved address: $connect_address"
	fi

	# Try auto-discovery if no saved address
	if [[ -z $connect_address ]]; then
		echo ""
		log "Searching for Android devices on network..."
		connect_address=$(discover_android_device)
	fi

	# Manual fallback
	if [[ -z $connect_address ]]; then
		echo ""
		echo "Auto-discovery failed. Enter address manually."
		echo "On phone: Settings > Developer Options > Wireless debugging"
		echo "Look for IP address & Port (NOT the pairing port)"
		echo ""
		read -rp "Enter connection IP:port (e.g., 192.168.1.100:41567): " connect_address

		if [[ -z $connect_address ]]; then
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
		if [[ -f $WIRELESS_CONFIG ]]; then
			read -rp "Try connecting to saved wireless device? [Y/n]: " try_wireless
			if [[ ${try_wireless,,} != "n" ]]; then
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

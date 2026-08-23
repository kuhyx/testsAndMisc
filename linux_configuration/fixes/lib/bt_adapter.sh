#!/bin/bash
# Firmware download and stuck-adapter recovery.
#
# Sourced by fix_bluetooth.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# ==========================================================================
# 3. Check for missing Broadcom firmware
# ==========================================================================
check_firmware() {
	echo ""
	log_info "Checking for missing Bluetooth firmware..."

	local missing_fw
	missing_fw=$(dmesg 2>/dev/null | grep -o "brcm/BCM[^ ']*\.hcd" | sort -u || true)

	if [[ -z $missing_fw ]]; then
		log_ok "No missing firmware detected in dmesg."
		return 0
	fi

	local fw_name
	for fw_name in $missing_fw; do
		local fw_path="/usr/lib/firmware/$fw_name"
		if [[ -f $fw_path ]]; then
			log_ok "Firmware $fw_name already installed."
			continue
		fi

		local basename
		basename=$(basename "$fw_name")
		local url="https://github.com/winterheart/broadcom-bt-firmware/raw/master/brcm/$basename"

		log_warn "Missing firmware: $fw_name"
		apply_fix "Downloading $basename from broadcom-bt-firmware repo" \
			_download_firmware "$url" "$fw_path"
	done
}

_download_firmware() {
	local url="$1"
	local dest="$2"
	mkdir -p "$(dirname "$dest")"
	wget -q "$url" -O "$dest" || curl -sL "$url" -o "$dest"
}

# ==========================================================================
# 4. Reset stuck adapter via USB reset
# ==========================================================================
check_adapter_stuck() {
	echo ""
	log_info "Checking if Bluetooth adapter is responsive..."

	# Test if bluetoothctl can see the adapter
	local adapter_list
	adapter_list=$(_btctl list | grep "^Controller" || true)

	if [[ -n $adapter_list ]]; then
		log_ok "Adapter is responsive: $adapter_list"
		return 0
	fi

	log_warn "Adapter not responding to bluetoothctl."

	# Try USB reset if usbreset is available
	local bt_usb
	bt_usb=$(lsusb 2>/dev/null | grep -i bluetooth | head -1 || true)
	if [[ -n $bt_usb ]]; then
		local usb_id
		usb_id=$(echo "$bt_usb" | grep -oP 'ID \K[0-9a-f]{4}:[0-9a-f]{4}')
		if [[ -n $usb_id ]] && has_cmd usbreset; then
			apply_fix "USB-resetting Bluetooth adapter ($usb_id)" \
				usbreset "$usb_id"
		else
			log_info "Falling back to btusb module reload..."
			apply_fix "Reloading btusb kernel module" \
				_reload_btusb
		fi
	else
		log_error "No USB Bluetooth adapter found. Is the dongle plugged in?"
	fi
}

_reload_btusb() {
	modprobe -r btusb && sleep 1 && modprobe btusb && sleep 2
}

# ---------------------------------------------------------------------------
# Helper: check if A2DP services are resolved for a connected device
# Returns 0 if resolved, 1 otherwise.
# ---------------------------------------------------------------------------
_services_resolved() {
	local mac="$1"
	local dbus_path="/org/bluez/hci0/dev_${mac//:/_}"
	local result
	result=$(dbus-send --system --print-reply \
		--dest=org.bluez "$dbus_path" \
		org.freedesktop.DBus.Properties.Get \
		string:"org.bluez.Device1" string:"ServicesResolved" 2>/dev/null || true)
	echo "$result" | grep -q "boolean true"
}

# ---------------------------------------------------------------------------
# Helper: full reset cycle — btusb reload + service restarts + reconnect.
# Fixes stale HCI link state ("link tx timeout" / ServicesResolved stuck).
# ---------------------------------------------------------------------------
_full_adapter_reset_and_connect() {
	local mac="$1"

	log_info "Performing full adapter reset (btusb reload)..."
	_btctl disconnect "$mac" >/dev/null 2>&1 || true
	sleep 1

	modprobe -r btusb && sleep 2 && modprobe btusb && sleep 5
	systemctl restart bluetooth.service
	sleep 3

	_restart_pipewire_stack
	sleep 3

	log_info "Reconnecting to $mac after adapter reset..."
	{ echo "agent on"; echo "default-agent"; sleep 1; echo "power on"; sleep 1; echo "connect $mac"; sleep 20; } \
		| bluetoothctl 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Helper: verify the Bluetooth audio sink appeared in PipeWire.
# ---------------------------------------------------------------------------
_verify_audio_sink() {
	local mac="$1"
	local card_name="bluez_card.${mac//:/_}"

	if ! has_cmd pactl; then
		return 0
	fi

	# Give PipeWire time to create the audio card
	local _attempt
	for _attempt in 1 2 3 4 5; do
		if _run_as_user pactl list cards short 2>/dev/null | grep -q "$card_name"; then
			log_ok "Bluetooth audio card detected in PipeWire."
			return 0
		fi
		sleep 3
	done

	log_warn "Bluetooth audio card not found in PipeWire after connection."
	return 1
}
